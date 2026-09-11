import { z } from 'zod'


const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  DATABASE_URL: z.string().min(1),
  SUPABASE_URL: z.string().url(),
  serviceRoleKey: z.string().min(20),
  WHATSAPP_SESSION_ENCRYPTION_KEY: z.string().min(40),
  WHATSAPP_WEBHOOK_SECRET: z.string().min(32),
  WHATSAPP_BACKEND_WEBHOOK_URL: z.string().url(),
  WHATSAPP_ADMIN_LOCAL: z.string().default('true'),
  WHATSAPP_BRIDGE_HOST: z.string().default('127.0.0.1'),
  WHATSAPP_BRIDGE_PORT: z.coerce.number().int().min(1).max(65535).default(3001),
  WHATSAPP_MAX_MEDIA_MB: z.coerce.number().int().min(1).max(100).default(20),
  WHATSAPP_MIN_SEND_INTERVAL_MS: z.coerce.number().int().min(250).default(1000),
})


const parsed = schema.parse({
  ...process.env,
  serviceRoleKey: process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SECRET_KEY,
})

export const config = {
  ...parsed,
  adminLocal: parsed.NODE_ENV === 'development' && parsed.WHATSAPP_ADMIN_LOCAL.toLowerCase() === 'true',
  maxMediaBytes: parsed.WHATSAPP_MAX_MEDIA_MB * 1024 * 1024,
}
