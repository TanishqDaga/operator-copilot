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

export const api = {
  get: (path) => fetch(`/api${path}`, { cache: 'no-store' }).then(handle),
  post: (path, body) =>
    fetch(`/api${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body ?? {}),
    }).then(handle),
}
