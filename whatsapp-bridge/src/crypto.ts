import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto'


export type EncryptedValue = {
  ciphertext: Buffer
  nonce: Buffer
  authTag: Buffer
}


export function decodeEncryptionKey(encoded: string): Buffer {
  const key = Buffer.from(encoded, 'base64')
  if (key.length !== 32) throw new Error('WHATSAPP_SESSION_ENCRYPTION_KEY debe contener exactamente 32 bytes en base64')
  return key
}


export function encryptValue(plaintext: Buffer, key: Buffer, aad: string): EncryptedValue {
  const nonce = randomBytes(12)
  const cipher = createCipheriv('aes-256-gcm', key, nonce)
  cipher.setAAD(Buffer.from(aad))
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()])
  return { ciphertext, nonce, authTag: cipher.getAuthTag() }
}


export function decryptValue(value: EncryptedValue, key: Buffer, aad: string): Buffer {
  const decipher = createDecipheriv('aes-256-gcm', key, value.nonce)
  decipher.setAAD(Buffer.from(aad))
  decipher.setAuthTag(value.authTag)
  return Buffer.concat([decipher.update(value.ciphertext), decipher.final()])
}
