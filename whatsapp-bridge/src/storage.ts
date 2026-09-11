import { createHash, randomUUID } from 'node:crypto'
import { Readable, Transform, type TransformCallback } from 'node:stream'

import { downloadMediaMessage, type WAMessage } from '@whiskeysockets/baileys'

import { config } from './config.js'


class LimitedStream extends Transform {
  bytes = 0
  readonly hash = createHash('sha256')

  override _transform(chunk: Buffer, _encoding: BufferEncoding, callback: TransformCallback): void {
    this.bytes += chunk.length
    if (this.bytes > config.maxMediaBytes) {
      callback(new Error('El archivo supera WHATSAPP_MAX_MEDIA_MB'))
      return
    }
    this.hash.update(chunk)
    callback(null, chunk)
  }
}


export async function uploadIncomingMedia(message: WAMessage, kind: string, chatJid: string): Promise<Record<string, unknown>> {
  const source = await downloadMediaMessage(message, 'stream', {})
  if (!(source instanceof Readable)) throw new Error('Baileys no devolvió un stream de medio')
  const limited = source.pipe(new LimitedStream())
  const safeChat = chatJid.replace(/[^a-zA-Z0-9_.-]/g, '_')
  const path = `${safeChat}/${new Date().toISOString().slice(0, 10)}/${randomUUID()}`
  const request: RequestInit & { duplex: 'half' } = {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${config.serviceRoleKey}`,
      apikey: config.serviceRoleKey,
      'Content-Type': 'application/octet-stream',
      'x-upsert': 'false',
    },
    body: Readable.toWeb(limited) as ReadableStream<Uint8Array>,
    duplex: 'half',
  }
  const response = await fetch(`${config.SUPABASE_URL}/storage/v1/object/whatsapp-media/${path}`, request)
  if (!response.ok) throw new Error(`No fue posible guardar el medio (${response.status})`)
  return {
    media_kind: kind,
    storage_bucket: 'whatsapp-media',
    storage_path: path,
    size_bytes: limited.bytes,
    sha256: limited.hash.digest('hex'),
  }
}


export async function downloadStoredMedia(path: string): Promise<Readable> {
  const response = await fetch(`${config.SUPABASE_URL}/storage/v1/object/authenticated/whatsapp-media/${encodeURI(path)}`, {
    headers: {
      Authorization: `Bearer ${config.serviceRoleKey}`,
      apikey: config.serviceRoleKey,
    },
  })
  if (!response.ok) throw new Error(`No fue posible leer el medio (${response.status})`)
  const declaredSize = Number(response.headers.get('content-length'))
  if (Number.isFinite(declaredSize) && declaredSize > config.maxMediaBytes) {
    throw new Error('El archivo supera WHATSAPP_MAX_MEDIA_MB')
  }
  if (!response.body) throw new Error('Supabase no devolvió un stream de medio')
  return Readable.fromWeb(response.body as import('node:stream/web').ReadableStream<Uint8Array>)
    .pipe(new LimitedStream())
}
