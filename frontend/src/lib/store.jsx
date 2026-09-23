import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { loadSession, saveSession } from './session'

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
  const [session, setSession] = useState(loadSession)
  const [planner, setPlanner] = useState(null)
  const [schedule, setSchedule] = useState(null)
  const [operatorPlan, setOperatorPlan] = useState(null)
  const [plannerLoading, setPlannerLoading] = useState(false)
  const [plannerError, setPlannerError] = useState(null)
  const lastEventId = useRef(null)
  const prevLevel = useRef('SAFE')
  const role = session?.role || null
  const hasHeadline = useRef(false)

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
      hasHeadline.current = !!s?.alerts?.headline
      if (hasHeadline.current) setToasts([])
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
      if (lastEventId.current !== null && newest > lastEventId.current && !hasHeadline.current) {
        const fresh = ev.filter((e) => e.id > lastEventId.current && TOAST_KINDS.has(e.kind) && e.level !== 'SAFE')
        const prefer = fresh.find((e) => e.level === 'CRITICAL') || fresh[0]
        if (prefer) {
          setToasts((t) => [{ ...prefer, key: `${prefer.id}-${Date.now()}` }, ...t].slice(0, 2))
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

  // ---- demo session (see session.js — not real authentication) ----
  const login = useCallback((r, id, name) => {
    const s = { role: r, id, name }
    saveSession(s)
    setSession(s)
    setPlanner(null)
    setSchedule(null)
    setOperatorPlan(null)
  }, [])
  const logout = useCallback(() => {
    saveSession(null)
    setSession(null)
    setPlanner(null)
    setSchedule(null)
    setOperatorPlan(null)
  }, [])

  // ---- weather-aware planner: manager sees the whole plan, operator only their published schedule ----
  const refreshPlanner = useCallback(async () => {
    try { setPlanner(await api.get('/planner')); setPlannerError(null) } catch (e) { setPlannerError(e.message) }
  }, [])
  const refreshSchedule = useCallback(async () => {
    try { setSchedule(await api.get('/operator/schedule')) } catch { /* offline handled by state poll */ }
  }, [])
  usePoll(refreshPlanner, 5000, role === 'manager')
  usePoll(refreshSchedule, 3000, role === 'operator')
  // operator task planner: execution guidance on top of the published schedule (read-only)
  usePoll(async () => {
    try { setOperatorPlan(await api.get('/operator/planner')) } catch { /* offline handled by state poll */ }
  }, 2000, role === 'operator')

  const plannerAction = useCallback(async (call) => {
    setPlannerLoading(true)
    try {
      const v = await call()
      if (v?.tasks) setPlanner(v)
      return v
    } finally {
      setPlannerLoading(false)
    }
  }, [])
  const manager = useMemo(() => ({
    createTask: (task) => plannerAction(() => api.post('/planner/tasks', task)),
    updateTask: (id, task) => plannerAction(() => api.put(`/planner/tasks/${id}`, task)),
    deleteTask: (id) => plannerAction(() => api.del(`/planner/tasks/${id}`)),
    assign: (taskId, operatorId, machineId) =>
      plannerAction(() => api.post('/planner/assign', { task_id: taskId, operator_id: operatorId || null, machine_id: machineId || null })),
    recommend: () => plannerAction(() => api.post('/planner/recommend')),
    replan: () => plannerAction(() => api.post('/planner/replan')),
    override: (body) => plannerAction(() => api.post('/planner/override', body)),
    accept: () => plannerAction(() => api.post('/planner/accept')),
    publish: () => plannerAction(() => api.post('/planner/publish')),
    reset: () => plannerAction(() => api.post('/planner/reset')),
    setScenario: (scenario) => plannerAction(() => api.post('/weather/scenario', { scenario })),
  }), [plannerAction])
  const acknowledgeSchedule = useCallback(async () => setSchedule(await api.post('/operator/schedule/ack')), [])
  const forecast = planner?.forecast || schedule?.forecast || state?.planning?.forecast || null

  return (
    <Ctx.Provider
      value={{
        state, meta, events, tasks, online, active, started, toasts, dismissToast,
        explanation, explaining, explain, sim, refreshAll, simOpen, setSimOpen,
        session, role, login, logout, forecast, planner, schedule, plannerLoading, plannerError,
        refreshPlanner, refreshSchedule, manager, acknowledgeSchedule, operatorPlan,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}
