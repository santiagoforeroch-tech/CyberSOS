import { getContentType, type WAMessage } from '@whiskeysockets/baileys'


type CanonicalType = 'text' | 'image' | 'video' | 'audio' | 'document' | 'sticker' | 'location' | 'contact' | 'poll' | 'reaction' | 'unknown'

function unwrap(content: Record<string, any> | null | undefined): Record<string, any> {
  let current = content ?? {}
  while (true) {
    const nested = current.ephemeralMessage?.message
      ?? current.viewOnceMessage?.message
      ?? current.viewOnceMessageV2?.message
      ?? current.viewOnceMessageV2Extension?.message
    if (!nested) return current
    current = nested
  }
}

function timestamp(value: unknown): string {
  if (typeof value === 'number') return new Date(value * 1000).toISOString()
  if (typeof value === 'object' && value && 'toNumber' in value) {
    return new Date((value as { toNumber(): number }).toNumber() * 1000).toISOString()
  }
  return new Date().toISOString()
}

export function normalizeIncomingMessage(message: WAMessage): Record<string, unknown> | null {
  if (!message.key.id || !message.key.remoteJid || !message.message) return null
  const content = unwrap(message.message as Record<string, any>)
  const contentType = getContentType(content)
  const body = contentType ? content[contentType] : undefined
  let messageType: CanonicalType = 'unknown'
  let text: string | undefined
  let caption: string | undefined
  const metadata: Record<string, unknown> = {}

  switch (contentType) {
    case 'conversation':
      messageType = 'text'
      text = String(body ?? '')
      break
    case 'extendedTextMessage':
      messageType = 'text'
      text = body?.text
      break
    case 'imageMessage': messageType = 'image'; caption = body?.caption; break
    case 'videoMessage': messageType = 'video'; caption = body?.caption; break
    case 'audioMessage': messageType = 'audio'; metadata.voice_note = Boolean(body?.ptt); break
    case 'documentMessage': messageType = 'document'; caption = body?.caption; metadata.file_name = body?.fileName; break
    case 'stickerMessage': messageType = 'sticker'; break
    case 'locationMessage':
      messageType = 'location'
      metadata.latitude = body?.degreesLatitude
      metadata.longitude = body?.degreesLongitude
      metadata.name = body?.name
      metadata.address = body?.address
      break
    case 'contactMessage':
      messageType = 'contact'
      text = body?.displayName
      metadata.vcard = body?.vcard
      break
    case 'contactsArrayMessage':
      messageType = 'contact'
      text = body?.displayName
      metadata.contacts = body?.contacts
      break
    case 'pollCreationMessage':
    case 'pollCreationMessageV2':
    case 'pollCreationMessageV3':
      messageType = 'poll'
      text = body?.name
      metadata.options = body?.options?.map((option: any) => option.optionName)
      metadata.selectable_count = body?.selectableOptionsCount ?? 1
      break
    case 'reactionMessage':
      messageType = 'reaction'
      text = body?.text
      metadata.target_wa_message_id = body?.key?.id
      break
  }

  const quoted = body?.contextInfo?.stanzaId
  return {
    wa_message_id: message.key.id,
    chat_jid: message.key.remoteJid,
    sender_jid: message.key.participant ?? message.key.remoteJid,
    message_type: messageType,
    text,
    caption,
    quoted_wa_message_id: quoted,
    occurred_at: timestamp(message.messageTimestamp),
    metadata,
    has_media: ['image', 'video', 'audio', 'document', 'sticker'].includes(messageType),
  }
}


export function safeError(error: unknown): string {
  if (error instanceof Error) return error.message.slice(0, 500)
  return 'Error no identificado'
}
