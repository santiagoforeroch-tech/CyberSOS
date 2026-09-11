import { randomUUID } from 'node:crypto'

import pg from 'pg'

import { config } from './config.js'
import type { EncryptedValue } from './crypto.js'


const { Pool } = pg

export type OutboxRow = {
  id: string
  message_id: string
  command: Record<string, unknown>
  attempts: number
}

export type PollDefinition = {
  question: string
  options: string[]
  selectableCount: number
}

export type QuotedMessage = {
  key: { remoteJid: string; id: string; fromMe: boolean }
  message: { conversation: string }
}

export class BridgeRepository {
  readonly pool = new Pool({ connectionString: config.DATABASE_URL, max: 5 })
  readonly instanceId = randomUUID()

  async close(): Promise<void> {
    await this.pool.end()
  }

  async connectionId(): Promise<string> {
    const result = await this.pool.query<{ id: string }>(
      `insert into public.whatsapp_connections (session_key)
       values ('central') on conflict (session_key) do update set updated_at = now()
       returning id`,
    )
    return result.rows[0]!.id
  }

  async acquireLease(): Promise<boolean> {
    const result = await this.pool.query(
      `update public.whatsapp_connections
       set bridge_instance_id = $1, lease_expires_at = now() + interval '30 seconds', updated_at = now()
       where session_key = 'central'
         and (lease_expires_at is null or lease_expires_at < now() or bridge_instance_id = $1)
       returning id`,
      [this.instanceId],
    )
    return result.rowCount === 1
  }

  async renewLease(): Promise<boolean> {
    const result = await this.pool.query(
      `update public.whatsapp_connections
       set lease_expires_at = now() + interval '30 seconds', last_seen_at = now(), updated_at = now()
       where session_key = 'central' and bridge_instance_id = $1
       returning id`,
      [this.instanceId],
    )
    return result.rowCount === 1
  }

  async releaseLease(): Promise<void> {
    await this.pool.query(
      `update public.whatsapp_connections
       set bridge_instance_id = null, lease_expires_at = null, updated_at = now()
       where session_key = 'central' and bridge_instance_id = $1`,
      [this.instanceId],
    )
  }

  async setConnectionState(state: string, fields: { accountJid?: string; displayName?: string; safeError?: string } = {}): Promise<void> {
    await this.pool.query(
      `update public.whatsapp_connections
       set state = $1,
           account_jid = coalesce($2, account_jid),
           display_name = coalesce($3, display_name),
           safe_error = $4,
           connected_at = case when $1 = 'connected' then coalesce(connected_at, now()) else connected_at end,
           updated_at = now()
       where session_key = 'central'`,
      [state, fields.accountJid ?? null, fields.displayName ?? null, fields.safeError ?? null],
    )
  }

  async connectionState(): Promise<Record<string, unknown>> {
    const result = await this.pool.query(
      `select state, account_jid, display_name, safe_error
       from public.whatsapp_connections where session_key = 'central'`,
    )
    return result.rows[0] ?? { state: 'disconnected' }
  }

  async getAuthItem(type: string, itemKey: string): Promise<EncryptedValue | null> {
    const connectionId = await this.connectionId()
    const result = await this.pool.query<{
      ciphertext: Buffer
      nonce: Buffer
      auth_tag: Buffer
    }>(
      `select ciphertext, nonce, auth_tag from public.whatsapp_auth_items
       where connection_id = $1 and item_type = $2 and item_key = $3`,
      [connectionId, type, itemKey],
    )
    const row = result.rows[0]
    return row ? { ciphertext: row.ciphertext, nonce: row.nonce, authTag: row.auth_tag } : null
  }

  async putAuthItem(type: string, itemKey: string, value: EncryptedValue): Promise<void> {
    const connectionId = await this.connectionId()
    await this.pool.query(
      `insert into public.whatsapp_auth_items
         (connection_id, item_type, item_key, ciphertext, nonce, auth_tag)
       values ($1, $2, $3, $4, $5, $6)
       on conflict (connection_id, item_type, item_key) do update
       set ciphertext = excluded.ciphertext, nonce = excluded.nonce,
           auth_tag = excluded.auth_tag, updated_at = now()`,
      [connectionId, type, itemKey, value.ciphertext, value.nonce, value.authTag],
    )
  }

  async deleteAuthItem(type: string, itemKey: string): Promise<void> {
    const connectionId = await this.connectionId()
    await this.pool.query(
      `delete from public.whatsapp_auth_items
       where connection_id = $1 and item_type = $2 and item_key = $3`,
      [connectionId, type, itemKey],
    )
  }

  async clearAuth(): Promise<void> {
    const connectionId = await this.connectionId()
    await this.pool.query('delete from public.whatsapp_auth_items where connection_id = $1', [connectionId])
  }

  async claimOutbox(): Promise<OutboxRow | null> {
    const result = await this.pool.query<OutboxRow>(
      'select * from public.claim_whatsapp_outbox($1, $2)',
      [this.instanceId, 30],
    )
    return result.rows[0] ?? null
  }

  async pollDefinition(chatJid: string | null | undefined, waMessageId: string | null | undefined): Promise<PollDefinition | null> {
    if (!chatJid || !waMessageId) return null
    const result = await this.pool.query<{
      text_content: string | null
      metadata: Record<string, unknown>
      command: Record<string, unknown> | null
    }>(
      `select m.text_content, m.metadata, o.command
       from public.whatsapp_messages m
       join public.whatsapp_conversations c on c.id = m.conversation_id
       left join public.whatsapp_outbox o on o.message_id = m.id
       where c.chat_jid = $1 and m.wa_message_id = $2 and m.message_type = 'poll'
       limit 1`,
      [chatJid, waMessageId],
    )
    const row = result.rows[0]
    if (!row) return null
    const command = row.command ?? {}
    const options = (command.options ?? row.metadata.options) as unknown
    if (!Array.isArray(options) || options.some((value) => typeof value !== 'string')) return null
    const selectable = Number(command.selectable_count ?? row.metadata.selectable_count ?? 1)
    return {
      question: String(command.question ?? row.text_content ?? 'Encuesta'),
      options: options as string[],
      selectableCount: Number.isInteger(selectable) && selectable > 0 ? selectable : 1,
    }
  }

  async quotedMessage(chatJid: string, waMessageId: string): Promise<QuotedMessage | null> {
    const result = await this.pool.query<{
      direction: string
      text_content: string | null
      caption: string | null
    }>(
      `select m.direction, m.text_content, m.caption
       from public.whatsapp_messages m
       join public.whatsapp_conversations c on c.id = m.conversation_id
       where c.chat_jid = $1 and m.wa_message_id = $2
       limit 1`,
      [chatJid, waMessageId],
    )
    const row = result.rows[0]
    if (!row) return null
    return {
      key: { remoteJid: chatJid, id: waMessageId, fromMe: row.direction === 'outbound' },
      message: { conversation: row.text_content ?? row.caption ?? 'Mensaje citado' },
    }
  }

  async completeOutbox(row: OutboxRow, waMessageId: string): Promise<void> {
    const client = await this.pool.connect()
    try {
      await client.query('begin')
      await client.query(
        `update public.whatsapp_outbox set state = 'sent', lease_owner = null,
         lease_expires_at = null, updated_at = now() where id = $1`,
        [row.id],
      )
      await client.query(
        `update public.whatsapp_messages set wa_message_id = $1, status = 'sent',
         updated_at = now() where id = $2`,
        [waMessageId, row.message_id],
      )
      await client.query('commit')
    } catch (error) {
      await client.query('rollback')
      throw error
    } finally {
      client.release()
    }
  }

  async failOutbox(row: OutboxRow, safeError: string): Promise<void> {
    const retry = row.attempts < 3
    await this.pool.query(
      `update public.whatsapp_outbox
       set state = $2, safe_error = $3, lease_owner = null, lease_expires_at = null,
           available_at = case when $2 = 'pending' then now() + make_interval(secs => least(60, power(2, attempts)::int)) else available_at end,
           updated_at = now()
       where id = $1`,
      [row.id, retry ? 'pending' : 'failed', safeError],
    )
    if (!retry) {
      await this.pool.query(
        `update public.whatsapp_messages set status = 'failed', safe_error = $1, updated_at = now()
         where id = $2`,
        [safeError, row.message_id],
      )
    }
  }

  async persistBridgeEvent(event: Record<string, unknown>): Promise<void> {
    await this.pool.query(
      `insert into public.whatsapp_bridge_events (event_id, event_type, payload, occurred_at)
       values ($1, $2, $3::jsonb, $4)
       on conflict (event_id) do nothing`,
      [event.event_id, event.event_type, JSON.stringify(event.payload), event.occurred_at],
    )
  }

  async markEventDelivered(eventId: string): Promise<void> {
    await this.pool.query(
      `update public.whatsapp_bridge_events set delivered_at = now(), processed_at = now()
       where event_id = $1`,
      [eventId],
    )
  }

  async pendingEvents(limit = 10): Promise<Record<string, unknown>[]> {
    const result = await this.pool.query(
      `select event_id, event_type, payload, occurred_at
       from public.whatsapp_bridge_events
       where processed_at is null and available_at <= now()
       order by created_at
       limit $1`,
      [limit],
    )
    return result.rows.map((row) => ({
      event_id: row.event_id,
      event_type: row.event_type,
      payload: row.payload,
      occurred_at: new Date(row.occurred_at).toISOString(),
    }))
  }

  async markEventFailure(eventId: string, error: string): Promise<void> {
    await this.pool.query(
      `update public.whatsapp_bridge_events
       set attempts = attempts + 1,
           safe_error = $2,
           available_at = now() + make_interval(secs => least(60, power(2, attempts + 1)::int))
       where event_id = $1`,
      [eventId, error],
    )
  }
}
