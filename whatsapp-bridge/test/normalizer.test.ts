import assert from 'node:assert/strict'
import { test } from 'node:test'

import { normalizeIncomingMessage } from '../src/normalizer.js'


test('normaliza texto entrante', () => {
  const result = normalizeIncomingMessage({
    key: { id: 'ABC', remoteJid: '573001234567@s.whatsapp.net', fromMe: false },
    message: { conversation: 'Hola' },
    messageTimestamp: 1_700_000_000,
  })
  assert.equal(result?.message_type, 'text')
  assert.equal(result?.text, 'Hola')
  assert.equal(result?.chat_jid, '573001234567@s.whatsapp.net')
})
