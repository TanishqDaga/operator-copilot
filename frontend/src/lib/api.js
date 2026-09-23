import { authHeaders } from './session'

async function handle(res) {
  if (!res.ok) {
    let msg = `${res.status}`
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : j.detail?.message || msg
    } catch { /* non-JSON error body */ }
    throw new Error(msg)
  }
  return res.json()
}

const send = (method) => (path, body) =>
  fetch(`/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body === undefined && method === 'DELETE' ? undefined : JSON.stringify(body ?? {}),
  }).then(handle)

export const api = {
  get: (path) => fetch(`/api${path}`, { cache: 'no-store', headers: authHeaders() }).then(handle),
  post: send('POST'),
  put: send('PUT'),
  del: send('DELETE'),
}
