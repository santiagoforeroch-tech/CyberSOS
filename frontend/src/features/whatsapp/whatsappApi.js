const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api"

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || "No fue posible comunicarse con WhatsApp")
  }
  return response.json()
}

export const whatsappApi = {
  capabilities: () => request("/whatsapp/admin/capabilities"),
  connection: () => request("/whatsapp/admin/connection"),
  start: () => request("/whatsapp/admin/connection/start", { method: "POST" }),
  reconnect: () => request("/whatsapp/admin/connection/reconnect", { method: "POST" }),
  qr: () => request("/whatsapp/admin/connection/qr"),
  logout: () => request("/whatsapp/admin/connection/session", { method: "DELETE" }),
  conversations: () => request("/whatsapp/admin/conversations"),
  messages: (id) => request(`/whatsapp/admin/conversations/${id}/messages`),
  sendText: (recipient, text, quotedMessageId = null) => request("/whatsapp/admin/messages/text", {
    method: "POST",
    body: JSON.stringify({ recipient, text, quoted_message_id: quotedMessageId }),
  }),
}
