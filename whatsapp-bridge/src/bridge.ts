import { createHmac, randomUUID } from 'node:crypto'

import { Boom } from '@hapi/boom'
import makeWASocket, {
  Browsers,
  DisconnectReason,
  getAggregateVotesInPollMessage,
  type WAMessage,
  type WASocket,
} from '@whiskeysockets/baileys'
import pino from 'pino'
import { z } from 'zod'

import { createDatabaseAuthState } from './auth-store.js'
import { config } from './config.js'
import { BridgeRepository, type OutboxRow } from './db.js'
import { normalizeIncomingMessage, safeError } from './normalizer.js'
import { downloadStoredMedia, uploadIncomingMedia } from './storage.js'


const logger = pino({ level: process.env.LOG_LEVEL ?? 'info' })

const commandSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('text'), recipient: z.string(), text: z.string().min(1), quoted_wa_message_id: z.string().nullish() }),
  z.object({
    kind: z.enum(['image', 'video', 'audio', 'document', 'sticker']),
    recipient: z.string(), storage_path: z.string(), mime_type: z.string(), caption: z.string().nullish(),
    quoted_wa_message_id: z.string().nullish(),
  }),
  z.object({
    kind: z.literal('location'), recipient: z.string(), latitude: z.number(), longitude: z.number(),
    name: z.string().nullish(), address: z.string().nullish(),
  }),
  z.object({ kind: z.literal('contact'), recipient: z.string(), display_name: z.string(), vcard: z.string() }),
  z.object({
    kind: z.literal('poll'), recipient: z.string(), question: z.string(), options: z.array(z.string()).min(2),
    selectable_count: z.number().int().positive(),
  }),
  z.object({ kind: z.literal('reaction'), recipient: z.string(), target_wa_message_id: z.string(), emoji: z.string() }),
])


export class WhatsAppBridge {
  private socket: WASocket | null = null
  private authClear: (() => Promise<void>) | null = null
  private leaseTimer: NodeJS.Timeout | null = null
  private outboxTimer: NodeJS.Timeout | null = null
  private eventTimer: NodeJS.Timeout | null = null
  private reconnectTimer: NodeJS.Timeout | null = null
  private reconnectAttempts = 0
  private qrValue: { value: string; expiresAt: number } | null = null
  private messageCache = new Map<string, WAMessage['message']>()
  private processingOutbox = false
  private manualStop = false

  constructor(readonly repository = new BridgeRepository()) {}

  async start(): Promise<void> {
    if (this.socket) return
    this.manualStop = false
    if (!await this.repository.acquireLease()) {
      throw new Error('Otra instancia del puente tiene la lease activa')
    }
    await this.repository.setConnectionState('starting')
    const auth = await createDatabaseAuthState(this.repository)
    this.authClear = auth.clear
    this.socket = makeWASocket({
      auth: auth.state,
      browser: Browsers.ubuntu('Proyecto estudiantil'),
      logger: logger.child({ component: 'baileys' }),
      markOnlineOnConnect: false,
      getMessage: async (key) => {
        const cached = this.messageCache.get(`${key.remoteJid}:${key.id}`)
        if (cached) return cached
        const poll = await this.repository.pollDefinition(key.remoteJid, key.id)
        if (!poll) return undefined
        return {
          pollCreationMessage: {
            name: poll.question,
            options: poll.options.map((optionName) => ({ optionName })),
            selectableOptionsCount: poll.selectableCount,
          },
        }
      },
    })

    this.socket.ev.on('creds.update', auth.saveCreds)
    this.socket.ev.on('connection.update', async (update) => {
      if (update.qr) {
        this.qrValue = { value: update.qr, expiresAt: Date.now() + 60_000 }
        await this.repository.setConnectionState('qr')
      }
      if (update.connection === 'open') {
        this.qrValue = null
        this.reconnectAttempts = 0
        await this.repository.setConnectionState('connected', {
          accountJid: this.socket?.user?.id,
          displayName: this.socket?.user?.name ?? undefined,
        })
      }
      if (update.connection === 'close') {
        if (this.manualStop) return
        const code = new Boom(update.lastDisconnect?.error).output.statusCode
        const loggedOut = code === DisconnectReason.loggedOut
        this.socket = null
        if (loggedOut) {
          await this.repository.setConnectionState('logged_out')
          return
        }
        await this.repository.setConnectionState('reconnecting', { safeError: safeError(update.lastDisconnect?.error) })
        this.scheduleReconnect()
      }
    })

    this.socket.ev.on('messages.upsert', async ({ type, messages }) => {
      if (type !== 'notify') return
      for (const message of messages) {
        if (message.key.fromMe || !message.key.id || !message.key.remoteJid) continue
        this.messageCache.set(`${message.key.remoteJid}:${message.key.id}`, message.message)
        const normalized = normalizeIncomingMessage(message)
        if (!normalized) continue
        if (normalized.has_media) {
          try {
            normalized.media = await uploadIncomingMedia(message, String(normalized.message_type), message.key.remoteJid)
          } catch (error) {
            normalized.media_error = safeError(error)
          }
        }
        delete normalized.has_media
        await this.emitEvent('message.received', normalized, String(normalized.occurred_at))
      }
    })

    this.socket.ev.on('messages.update', async (updates) => {
      for (const { key, update } of updates) {
        if (update.pollUpdates) {
          const original = this.messageCache.get(`${key.remoteJid}:${key.id}`)
          if (original) {
            const votes = getAggregateVotesInPollMessage({ message: original, pollUpdates: update.pollUpdates })
            await this.emitEvent('poll.updated', { wa_message_id: key.id, chat_jid: key.remoteJid, votes })
          }
        }
        if (update.status !== undefined) {
          await this.emitEvent('message.status', {
            wa_message_id: key.id,
            chat_jid: key.remoteJid,
            status_code: update.status,
          })
        }
      }
    })

    this.leaseTimer ??= setInterval(() => {
      this.repository.renewLease().then((ok) => {
        if (!ok) void this.stop(new Error('Se perdió la lease de la sesión'))
      }).catch((error) => logger.error({ error: safeError(error) }, 'No se pudo renovar la lease'))
    }, 10_000)
    this.outboxTimer ??= setInterval(() => void this.processOutbox(), config.WHATSAPP_MIN_SEND_INTERVAL_MS)
    this.eventTimer ??= setInterval(() => void this.retryEvents(), 5000)
  }

  async reconnect(): Promise<void> {
    await this.stop()
    await this.start()
  }

  async logout(): Promise<void> {
    if (this.socket) await this.socket.logout()
    if (this.authClear) await this.authClear()
    this.socket = null
    this.qrValue = null
    await this.repository.setConnectionState('logged_out')
  }

  getQr(): string | null {
    if (!this.qrValue || this.qrValue.expiresAt < Date.now()) {
      this.qrValue = null
      return null
    }
    return this.qrValue.value
  }

  async status(): Promise<Record<string, unknown>> {
    return this.repository.connectionState()
  }

  async stop(reason?: Error): Promise<void> {
    this.manualStop = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.leaseTimer) clearInterval(this.leaseTimer)
    if (this.outboxTimer) clearInterval(this.outboxTimer)
    if (this.eventTimer) clearInterval(this.eventTimer)
    this.reconnectTimer = this.leaseTimer = this.outboxTimer = this.eventTimer = null
    if (this.socket) this.socket.end(reason)
    this.socket = null
    await this.repository.releaseLease()
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    const delay = Math.min(60_000, 1000 * 2 ** this.reconnectAttempts) + Math.floor(Math.random() * 500)
    this.reconnectAttempts += 1
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.start().catch((error) => {
        logger.error({ error: safeError(error) }, 'Reconexión fallida')
        this.scheduleReconnect()
      })
    }, delay)
  }

  private async processOutbox(): Promise<void> {
    if (!this.socket?.user || this.processingOutbox) return
    this.processingOutbox = true
    let row: OutboxRow | null = null
    try {
      row = await this.repository.claimOutbox()
      if (!row) return
      const command = commandSchema.parse(row.command)
      const sent = await this.sendCommand(command)
      if (!sent?.key.id) throw new Error('WhatsApp no devolvió identificador del mensaje')
      if (sent.key.remoteJid && sent.message) {
        this.messageCache.set(`${sent.key.remoteJid}:${sent.key.id}`, sent.message)
      }
      await this.repository.completeOutbox(row, sent.key.id)
    } catch (error) {
      logger.warn({ error: safeError(error), outboxId: row?.id }, 'Fallo al enviar comando')
      if (row) await this.repository.failOutbox(row, safeError(error))
    } finally {
      this.processingOutbox = false
    }
  }

  private async sendCommand(command: z.infer<typeof commandSchema>): Promise<WAMessage | undefined> {
    if (!this.socket) throw new Error('WhatsApp no está conectado')
    switch (command.kind) {
      case 'text': {
        const quoted = command.quoted_wa_message_id
          ? await this.repository.quotedMessage(command.recipient, command.quoted_wa_message_id)
          : null
        return this.socket.sendMessage(command.recipient, { text: command.text }, quoted ? { quoted } : undefined)
      }
      case 'location': return this.socket.sendMessage(command.recipient, {
        location: {
          degreesLatitude: command.latitude,
          degreesLongitude: command.longitude,
          name: command.name ?? undefined,
          address: command.address ?? undefined,
        },
      })
      case 'contact': return this.socket.sendMessage(command.recipient, {
        contacts: { displayName: command.display_name, contacts: [{ vcard: command.vcard }] },
      })
      case 'poll': return this.socket.sendMessage(command.recipient, {
        poll: { name: command.question, values: command.options, selectableCount: command.selectable_count },
      })
      case 'reaction': return this.socket.sendMessage(command.recipient, {
        react: { text: command.emoji, key: { remoteJid: command.recipient, id: command.target_wa_message_id } },
      })
      default: {
        const stream = await downloadStoredMedia(command.storage_path)
        const content: Record<string, unknown> = { [command.kind]: { stream }, mimetype: command.mime_type }
        if ('caption' in command && command.caption) content.caption = command.caption
        const quoted = command.quoted_wa_message_id
          ? await this.repository.quotedMessage(command.recipient, command.quoted_wa_message_id)
          : null
        return this.socket.sendMessage(command.recipient, content as any, quoted ? { quoted } : undefined)
      }
    }
  }

  private async emitEvent(eventType: string, payload: Record<string, unknown>, occurredAt = new Date().toISOString()): Promise<void> {
    const event = { event_id: randomUUID(), event_type: eventType, occurred_at: occurredAt, payload }
    await this.repository.persistBridgeEvent(event)
    await this.deliverEvent(event)
  }

  private async retryEvents(): Promise<void> {
    for (const event of await this.repository.pendingEvents()) {
      await this.deliverEvent(event)
    }
  }

  private async deliverEvent(event: Record<string, unknown>): Promise<void> {
    const raw = JSON.stringify(event)
    const timestamp = Math.floor(Date.now() / 1000).toString()
    const signature = createHmac('sha256', config.WHATSAPP_WEBHOOK_SECRET).update(`${timestamp}.${raw}`).digest('hex')
    try {
      const response = await fetch(config.WHATSAPP_BACKEND_WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-WhatsApp-Timestamp': timestamp,
          'X-WhatsApp-Signature': `sha256=${signature}`,
        },
        body: raw,
      })
      if (!response.ok) throw new Error(`Webhook rechazado (${response.status})`)
      await this.repository.markEventDelivered(String(event.event_id))
    } catch (error) {
      await this.repository.markEventFailure(String(event.event_id), safeError(error))
      logger.warn({ error: safeError(error), eventId: event.event_id }, 'El webhook se reintentará')
    }
  }
}
