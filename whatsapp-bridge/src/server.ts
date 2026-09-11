import express from 'express'
import pino from 'pino'

import { WhatsAppBridge } from './bridge.js'
import { config } from './config.js'
import { safeError } from './normalizer.js'


const logger = pino({ level: process.env.LOG_LEVEL ?? 'info' })
const app = express()
const bridge = new WhatsAppBridge()

app.disable('x-powered-by')
app.use(express.json({ limit: '32kb' }))

app.get('/health', (_request, response) => response.json({ status: 'ok' }))

app.use('/admin', (request, response, next) => {
  if (!config.adminLocal || !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(request.socket.remoteAddress ?? '')) {
    response.sendStatus(404)
    return
  }
  response.setHeader('Cache-Control', 'no-store')
  next()
})

app.get('/admin/connection', async (_request, response) => response.json(await bridge.status()))
app.post('/admin/connection/start', async (_request, response) => {
  await bridge.start()
  response.status(202).json({ started: true })
})
app.post('/admin/connection/reconnect', async (_request, response) => {
  await bridge.reconnect()
  response.status(202).json({ reconnecting: true })
})
app.get('/admin/connection/qr', (_request, response) => {
  const qr = bridge.getQr()
  if (!qr) {
    response.status(404).json({ detail: 'No hay un QR vigente' })
    return
  }
  response.json({ qr })
})
app.delete('/admin/connection/session', async (_request, response) => {
  await bridge.logout()
  response.json({ logged_out: true })
})

app.use((error: unknown, _request: express.Request, response: express.Response, _next: express.NextFunction) => {
  logger.error({ error: safeError(error) }, 'Error del puente')
  response.status(500).json({ detail: safeError(error) })
})

const server = app.listen(config.WHATSAPP_BRIDGE_PORT, config.WHATSAPP_BRIDGE_HOST, () => {
  logger.info({ host: config.WHATSAPP_BRIDGE_HOST, port: config.WHATSAPP_BRIDGE_PORT }, 'Puente listo')
})

if (process.env.NODE_ENV === 'production') {
  bridge.start().catch((error) => logger.error({ error: safeError(error) }, 'No fue posible iniciar WhatsApp'))
}

async function shutdown(): Promise<void> {
  server.close()
  await bridge.stop()
  await bridge.repository.close()
  process.exit(0)
}

process.on('SIGTERM', () => void shutdown())
process.on('SIGINT', () => void shutdown())
