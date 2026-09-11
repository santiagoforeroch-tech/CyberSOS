const localApiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api`
const isLocalHost = ["localhost", "127.0.0.1"].includes(window.location.hostname)

// En producción el frontend usa el mismo origen. Vercel puede reenviar /api al
// backend sin introducir una URL local o un secreto en el bundle del navegador.
export const apiBaseUrl = import.meta.env.VITE_API_URL || (isLocalHost ? localApiUrl : "/api")

export function errorMessage(payload) {
  if (typeof payload?.message === 'string') return payload.message
  if (typeof payload?.detail === 'string') return payload.detail

  if (Array.isArray(payload?.detail)) {
    const firstError = payload.detail.find((item) => typeof item?.msg === 'string')
    if (firstError) {
      const field = Array.isArray(firstError.loc) ? firstError.loc.at(-1) : null
      return field ? `Revisa el campo ${field}: ${firstError.msg}` : firstError.msg
    }
  }

  return 'No fue posible completar la solicitud'
}

export async function apiRequest(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const response = await fetch(`${apiBaseUrl}${path}`, {
    credentials: 'include',
    headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...options.headers },
    ...options,
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(errorMessage(payload))
    error.status = response.status
    throw error
  }

  return response.status === 204 ? null : response.json()
}
