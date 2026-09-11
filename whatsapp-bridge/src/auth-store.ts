import {
  BufferJSON,
  initAuthCreds,
  proto,
  type AuthenticationCreds,
  type AuthenticationState,
  type SignalDataTypeMap,
} from '@whiskeysockets/baileys'

import { config } from './config.js'
import { decodeEncryptionKey, decryptValue, encryptValue } from './crypto.js'
import type { BridgeRepository } from './db.js'


const SESSION_ID = 'central'

function aad(type: string, key: string): string {
  return `${SESSION_ID}:${type}:${key}`
}


export async function createDatabaseAuthState(repository: BridgeRepository): Promise<{
  state: AuthenticationState
  saveCreds: () => Promise<void>
  clear: () => Promise<void>
}> {
  const encryptionKey = decodeEncryptionKey(config.WHATSAPP_SESSION_ENCRYPTION_KEY)

  async function read<T>(type: string, key: string): Promise<T | undefined> {
    const stored = await repository.getAuthItem(type, key)
    if (!stored) return undefined
    const plaintext = decryptValue(stored, encryptionKey, aad(type, key)).toString('utf8')
    return JSON.parse(plaintext, BufferJSON.reviver) as T
  }

  async function write(type: string, key: string, value: unknown): Promise<void> {
    if (value === null || value === undefined) {
      await repository.deleteAuthItem(type, key)
      return
    }
    const plaintext = Buffer.from(JSON.stringify(value, BufferJSON.replacer))
    await repository.putAuthItem(type, key, encryptValue(plaintext, encryptionKey, aad(type, key)))
  }

  const creds = (await read<AuthenticationCreds>('creds', 'main')) ?? initAuthCreds()

  const state: AuthenticationState = {
    creds,
    keys: {
      get: async <T extends keyof SignalDataTypeMap>(type: T, ids: string[]) => {
        const result: { [id: string]: SignalDataTypeMap[T] } = {}
        await Promise.all(ids.map(async (id) => {
          let value = await read<SignalDataTypeMap[T]>(String(type), id)
          if (type === 'app-state-sync-key' && value) {
            value = proto.Message.AppStateSyncKeyData.fromObject(value as unknown as Record<string, unknown>) as unknown as SignalDataTypeMap[T]
          }
          if (value) result[id] = value
        }))
        return result
      },
      set: async (data) => {
        const writes: Promise<void>[] = []
        for (const category of Object.keys(data) as (keyof SignalDataTypeMap)[]) {
          const values = data[category]
          if (!values) continue
          for (const [id, value] of Object.entries(values)) {
            writes.push(write(String(category), id, value))
          }
        }
        await Promise.all(writes)
      },
      clear: async () => repository.clearAuth(),
    },
  }

  return {
    state,
    saveCreds: () => write('creds', 'main', state.creds),
    clear: () => repository.clearAuth(),
  }
}
