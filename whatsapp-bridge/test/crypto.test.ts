import assert from 'node:assert/strict'
import { test } from 'node:test'

import { decryptValue, encryptValue } from '../src/crypto.js'


test('cifra y descifra con AAD', () => {
  const key = Buffer.alloc(32, 7)
  const encrypted = encryptValue(Buffer.from('sesión'), key, 'central:creds:main')
  assert.equal(decryptValue(encrypted, key, 'central:creds:main').toString(), 'sesión')
  assert.throws(() => decryptValue(encrypted, key, 'otro'))
})
