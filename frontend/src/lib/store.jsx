import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from './api'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

const TOAST_KINDS = new Set(['safety', 'anomaly', 'eta', 'notice', 'task'])

function usePoll(fn, ms, enabled = true) {
  const saved = useRef(fn)
  saved.current = fn
  useEffect(() => {
    if (!enabled) return
    let alive = true
    let timer
    const run = async () => {
      await saved.current()
      if (alive) timer = setTimeout(run, ms)
    }
    run()
    return () => { alive = false; clearTimeout(timer) }
  }, [ms, enabled])
}

export function AppProvider({ children }) {
  const [state, setState] = useState(null)
  const [meta, setMeta] = useState(null)
  const [events, setEvents] = useState([])
  const [tasks, setTasks] = useState(null)
  const [online, setOnline] = useState(true)
  const [toasts, setToasts] = useState([])
  const [explanation, setExplanation] = useState(null)
  const [explaining, setExplaining] = useState(false)
  const [simOpen, setSimOpen] = useState(false)
  const lastEventId = useRef(null)
  const prevLevel = useRef('SAFE')

  const active = !!state?.shift?.active
  const started = active || !!state?.shift?.ended

  const loadMeta = useCallback(() => api.get('/meta').then(setMeta).catch(() => {}), [])
  useEffect(() => { loadMeta() }, [loadMeta])
  useEffect(() => { if (state && !meta) loadMeta() }, [state, meta, loadMeta]) // backend came up after first load

  // GET /api/state every 1 s — the single live feed for every screen
  usePoll(async () => {
    try {
      const s = await api.get('/state')
      setState(s)
      setOnline(true)
    } catch {
      setOnline(false)
    }
  }, 1000)

  usePoll(async () => {
    try {
      const ev = await api.get('/events')
      setEvents(ev)
      const newest = ev[0]?.id ?? 0
      if (lastEventId.current !== null && newest > lastEventId.current) {
        const fresh = ev.filter((e) => e.id > lastEventId.current && TOAST_KINDS.has(e.kind) && e.level !== 'SAFE')
        if (fresh.length) {
          setToasts((t) => [...fresh.slice(0, 3).map((e) => ({ ...e, key: `${e.id}-${Date.now()}` })), ...t].slice(0, 4))
        }
      }
      lastEventId.current = newest
    } catch { /* offline handled by state poll */ }
  }, 1000, started)

  usePoll(async () => {
    try { setTasks(await api.get('/tasks')) } catch { /* ignore */ }
  }, 2500, started)

  // toasts expire
  useEffect(() => {
    if (!toasts.length) return
    const t = setTimeout(() => setToasts((x) => x.slice(0, -1)), 5500)
    return () => clearTimeout(t)
  }, [toasts])

  const explain = useCallback(async (eventId) => {
    setExplaining(true)
    try {
      const r = await api.post('/explain', eventId ? { event_id: eventId } : {})
      const e = { ...r, at: new Date().toLocaleTimeString([], { hour12: false }), eventId }
      if (!eventId) setExplanation(e)
      return e
    } finally {
      setExplaining(false)
    }
  }, [])

  // auto-explain the moment the rule engine goes CRITICAL
  useEffect(() => {
    const lvl = state?.safety?.level
    if (!lvl) return
    if (lvl === 'CRITICAL' && prevLevel.current !== 'CRITICAL') explain().catch(() => {})
    prevLevel.current = lvl
  }, [state?.safety?.level, explain])

  const sim = useCallback(async (action, value) => {
    const s = await api.post('/sim', { action, value })
    setState(s)
    return s
  }, [])

  const refreshAll = useCallback(async () => {
    const [s, ev, t] = await Promise.all([api.get('/state'), api.get('/events'), api.get('/tasks')])
    setState(s); setEvents(ev); setTasks(t)
    lastEventId.current = ev[0]?.id ?? 0
    setExplanation(null)
    loadMeta()
  }, [loadMeta])

  const dismissToast = (key) => setToasts((t) => t.filter((x) => x.key !== key))

  return (
    <Ctx.Provider
      value={{
        state, meta, events, tasks, online, active, started, toasts, dismissToast,
        explanation, explaining, explain, sim, refreshAll, simOpen, setSimOpen,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}
