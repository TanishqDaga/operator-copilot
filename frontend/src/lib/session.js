/**
 * Demo session — NOT authentication. The chosen role/user lives in localStorage and is sent to the
 * backend as X-Demo-Role / X-Demo-User headers. Replace loadSession/saveSession/authHeaders with a
 * real auth provider later; nothing else in the app reads localStorage directly.
 */
const KEY = 'copilot.session'

export function loadSession() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || 'null')
    return s && (s.role === 'manager' || s.role === 'operator') && s.id ? s : null
  } catch {
    return null
  }
}

export function saveSession(session) {
  try {
    if (session) localStorage.setItem(KEY, JSON.stringify(session))
    else localStorage.removeItem(KEY)
  } catch { /* storage blocked — session lives in memory only */ }
}

export function authHeaders() {
  const s = loadSession()
  return s ? { 'X-Demo-Role': s.role, 'X-Demo-User': s.id } : {}
}

export const HOME = { manager: '/manager', operator: '/dashboard' }
