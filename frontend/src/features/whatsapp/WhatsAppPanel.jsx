import { useCallback, useEffect, useState } from "react"
import { QRCodeSVG } from "qrcode.react"

import { whatsappApi } from "./whatsappApi"
import "./whatsapp.css"


export function WhatsAppPanel() {
  const [connection, setConnection] = useState({ state: "disconnected" })
  const [qr, setQr] = useState(null)
  const [conversations, setConversations] = useState([])
  const [selected, setSelected] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const status = await whatsappApi.connection()
      setConnection(status)
      if (status.state === "qr") {
        const value = await whatsappApi.qr()
        setQr(value.qr)
      } else {
        setQr(null)
      }
      if (status.state === "connected") {
        setConversations(await whatsappApi.conversations())
      }
      setError("")
    } catch (refreshError) {
      setError(refreshError.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = window.setInterval(refresh, 3000)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function selectConversation(conversation) {
    setSelected(conversation)
    setMessages(await whatsappApi.messages(conversation.id))
  }

  async function sendText(event) {
    event.preventDefault()
    const text = draft.trim()
    if (!selected || !text) return
    await whatsappApi.sendText(selected.chat_jid, text)
    setDraft("")
    setMessages(await whatsappApi.messages(selected.id))
  }

  async function logout() {
    if (!window.confirm("¿Cerrar la sesión vinculada? Los mensajes guardados se conservarán.")) return
    await whatsappApi.logout()
    await refresh()
  }

  if (loading) return <section className="wa-panel">Cargando central de WhatsApp…</section>

  return (
    <section className="wa-panel" aria-labelledby="wa-title">
      <header className="wa-header">
        <div>
          <p className="wa-eyebrow">Canal central</p>
          <h1 id="wa-title">WhatsApp</h1>
          <p>Estado: <strong>{connection.state}</strong></p>
          <small className="wa-local-note">Disponible solo en desarrollo local con una cuenta dedicada.</small>
        </div>
        <div className="wa-actions">
          {connection.state === "disconnected" || connection.state === "logged_out" ? (
            <button onClick={() => whatsappApi.start().then(refresh)}>Conectar</button>
          ) : null}
          {connection.state === "error" ? (
            <button onClick={() => whatsappApi.reconnect().then(refresh)}>Reconectar</button>
          ) : null}
          {connection.state === "connected" ? (
            <button className="wa-danger" onClick={logout}>Cerrar sesión</button>
          ) : null}
        </div>
      </header>

      {error ? <p className="wa-error" role="alert">{error}</p> : null}
      {connection.safe_error ? <p className="wa-info" role="status">{connection.safe_error}</p> : null}

      {qr ? (
        <div className="wa-qr">
          <QRCodeSVG value={qr} size={240} aria-label="Código QR de WhatsApp" />
          <p>Escanéalo desde WhatsApp → Dispositivos vinculados. El código vence en un minuto y no se guarda.</p>
        </div>
      ) : null}

      {connection.state === "connected" ? (
        <div className="wa-layout">
          <aside className="wa-conversations" aria-label="Conversaciones">
            {conversations.length === 0 ? <p>Aún no hay mensajes nuevos.</p> : null}
            {conversations.map((conversation) => (
              <button
                className={selected?.id === conversation.id ? "is-active" : ""}
                key={conversation.id}
                onClick={() => selectConversation(conversation)}
              >
                <strong>{conversation.title || conversation.chat_jid}</strong>
                <span>{conversation.kind}</span>
              </button>
            ))}
          </aside>

          <main className="wa-thread">
            {!selected ? <p>Selecciona una conversación.</p> : (
              <>
                <div className="wa-messages" aria-live="polite">
                  {messages.map((message) => (
                    <article className={`wa-message ${message.direction}`} key={message.id}>
                      <small>{message.message_type} · {message.status}</small>
                      <p>{message.text_content || message.caption || "Mensaje multimedia"}</p>
                    </article>
                  ))}
                </div>
                <form className="wa-compose" onSubmit={sendText}>
                  <label htmlFor="wa-draft">Mensaje</label>
                  <textarea id="wa-draft" value={draft} onChange={(event) => setDraft(event.target.value)} />
                  <button type="submit">Enviar</button>
                </form>
              </>
            )}
          </main>
        </div>
      ) : null}
    </section>
  )
}
