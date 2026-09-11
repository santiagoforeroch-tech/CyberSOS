const localApiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api`
const API_URL = import.meta.env.VITE_API_URL ?? localApiUrl

export async function apiRequest(path, options = {}) {
  const isFormData = options.body instanceof FormData
  const response = await fetch(`${API_URL}${path}`, {
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
