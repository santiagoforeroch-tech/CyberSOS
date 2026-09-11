const localApiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api`
const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)

// En producción el frontend usa el mismo origen. Vercel puede reenviar /api al
// backend sin introducir una URL local o un secreto en el bundle del navegador.
export const apiBaseUrl = import.meta.env.VITE_API_URL || (isLocalHost ? localApiUrl : "/api")

export async function apiRequest(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: 'include',
    headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers },
    ...options,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload.message ?? payload.detail ?? 'No fue posible completar la solicitud')
    error.status = response.status
    throw error
  }

  return response.status === 204 ? null : response.json()
}
