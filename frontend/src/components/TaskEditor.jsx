import { Loader2, Save, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useApp } from '../lib/store'
import { SELECT } from './AssignmentSelector'
import { Segmented } from './ui'

const INPUT = 'h-10 w-full rounded-lg border border-line2 bg-panel2 px-3 text-sm text-ink focus:border-cat/60 focus:outline-none'
const LEVELS = ['low', 'medium', 'high']

function blank(meta, shift) {
  const type = meta?.task_types?.[0]?.value || 'load_truck'
  return {
    name: '', description: '', location: '', task_type: type, tonnes: 100, distance_m: 20, terrain: 'firm',
    estimated_duration_min: '', weather_sensitivity: { ...meta?.planning?.sensitivity_presets?.[type] },
    priority: 50, assigned_operator: '', assigned_machine: '', earliest_start: shift?.start || '09:00',
    latest_finish: shift?.end || '19:00', depends_on: [],
  }
}

/** Create / edit a planner task. `task` null = create. */
export default function TaskEditor({ open, task, tasks, onClose, onSave }) {
  const { meta, planner } = useApp()
  const [f, setF] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    if (!open) return
    setErr(null)
    setF(task ? {
      ...task, estimated_duration_min: task.estimated_duration_min ?? '', assigned_operator: task.assigned_operator || '',
      assigned_machine: task.assigned_machine || '', depends_on: task.depends_on || [],
    } : blank(meta, planner?.shift))
  }, [open, task, meta, planner?.shift])

  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open || !f) return null
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }))
  const presets = meta?.planning?.sensitivity_presets || {}

  const save = async (e) => {
    e.preventDefault()
    setBusy(true); setErr(null)
    try {
      await onSave({
        name: f.name, description: f.description, location: f.location, task_type: f.task_type,
        tonnes: Number(f.tonnes), distance_m: Number(f.distance_m), terrain: f.terrain,
        estimated_duration_min: f.estimated_duration_min === '' ? null : Number(f.estimated_duration_min),
        weather_sensitivity: f.weather_sensitivity, priority: Number(f.priority),
        assigned_operator: f.assigned_operator || null, assigned_machine: f.assigned_machine || null,
        earliest_start: f.earliest_start, latest_finish: f.latest_finish, depends_on: f.depends_on,
      })
      onClose()
    } catch (x) { setErr(x.message) } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 no-print">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={onClose} />
      <form onSubmit={save} className="absolute right-0 top-0 flex h-full w-full max-w-[560px] flex-col border-l border-line2 bg-panel animate-slideIn">
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <div className="font-semibold text-ink">{task ? `Edit ${task.id}` : 'Create task'}</div>
            <div className="text-2xs text-ink3">Changes mark the current recommendation as stale until you regenerate it</div>
          </div>
          <button type="button" className="btn btn-quiet h-10 w-10" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </header>
        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <Field label="Name"><input className={INPUT} value={f.name} onChange={(e) => set('name', e.target.value)} required maxLength={80} /></Field>
          <Field label="Description">
            <textarea className={`${INPUT} h-20 py-2`} value={f.description} onChange={(e) => set('description', e.target.value)} maxLength={400} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Location"><input className={INPUT} value={f.location} onChange={(e) => set('location', e.target.value)} /></Field>
            <Field label="Task type">
              <select className={SELECT + ' h-10'} value={f.task_type} onChange={(e) => set('task_type', e.target.value)}>
                {meta?.task_types?.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </Field>
            <Field label="Quantity (tonnes)"><input type="number" min={1} className={INPUT} value={f.tonnes} onChange={(e) => set('tonnes', e.target.value)} required /></Field>
            <Field label="Distance (m)"><input type="number" min={0} className={INPUT} value={f.distance_m} onChange={(e) => set('distance_m', e.target.value)} /></Field>
            <Field label="Terrain">
              <select className={SELECT + ' h-10'} value={f.terrain} onChange={(e) => set('terrain', e.target.value)}>
                {meta?.terrains?.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Estimated duration (min)" hint="Blank = use the ETA model baseline">
              <input type="number" min={5} max={720} className={INPUT} value={f.estimated_duration_min} placeholder="ETA model"
                onChange={(e) => set('estimated_duration_min', e.target.value)} />
            </Field>
            <Field label="Operator">
              <select className={SELECT + ' h-10'} value={f.assigned_operator} onChange={(e) => set('assigned_operator', e.target.value)}>
                <option value="">No operator</option>
                {meta?.operators?.map((o) => <option key={o.id} value={o.id}>{o.id} · {o.name}</option>)}
              </select>
            </Field>
            <Field label="Machine">
              <select className={SELECT + ' h-10'} value={f.assigned_machine} onChange={(e) => set('assigned_machine', e.target.value)}>
                <option value="">No machine</option>
                {meta?.machines?.map((m) => <option key={m.id} value={m.id}>{m.id} · {m.model}</option>)}
              </select>
            </Field>
            <Field label="Priority (0–100)"><input type="number" min={0} max={100} className={INPUT} value={f.priority} onChange={(e) => set('priority', e.target.value)} /></Field>
            <div />
            <Field label="Earliest start"><input type="time" step={300} className={`${INPUT} num`} value={f.earliest_start} onChange={(e) => set('earliest_start', e.target.value)} /></Field>
            <Field label="Latest finish"><input type="time" step={300} className={`${INPUT} num`} value={f.latest_finish} onChange={(e) => set('latest_finish', e.target.value)} /></Field>
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="label">Weather sensitivity profile</span>
              <select className="h-8 rounded-lg border border-line2 bg-panel2 px-2 text-xs text-ink" value=""
                onChange={(e) => e.target.value && set('weather_sensitivity', { ...presets[e.target.value] })} aria-label="Apply preset">
                <option value="">Apply preset…</option>
                {Object.keys(presets).map((k) => <option key={k} value={k}>{k.replace('_', ' ')}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              {['rain', 'wind', 'visibility'].map((fac) => (
                <div key={fac} className="grid grid-cols-[90px_1fr] items-center gap-3">
                  <span className="text-sm capitalize text-ink2">{fac}</span>
                  <Segmented value={f.weather_sensitivity?.[fac]} onChange={(v) => set('weather_sensitivity', { ...f.weather_sensitivity, [fac]: v })}
                    options={LEVELS.map((l) => ({ value: l, label: l }))} />
                </div>
              ))}
            </div>
            <p className="mt-2 text-2xs text-ink3">High = the planner strongly prefers good weather for this task; low = it can soak up poor-weather windows.</p>
          </div>

          {tasks?.length > 0 && (
            <Field label="Depends on" hint="Must finish before this task starts">
              <div className="flex flex-wrap gap-1.5">
                {tasks.filter((t) => t.id !== task?.id).map((t) => {
                  const on = f.depends_on.includes(t.id)
                  return (
                    <button type="button" key={t.id} onClick={() => set('depends_on', on ? f.depends_on.filter((d) => d !== t.id) : [...f.depends_on, t.id])}
                      className={`rounded-lg border px-2 py-1 text-xs ${on ? 'border-cat/60 bg-cat/10 text-cat' : 'border-line2 text-ink3 hover:text-ink2'}`}>
                      {t.id}
                    </button>
                  )
                })}
              </div>
            </Field>
          )}
          {err && <p className="rounded-lg border border-crit/40 bg-crit-bg px-3 py-2 text-sm text-crit">{err}</p>}
        </div>
        <footer className="flex items-center gap-3 border-t border-line px-5 py-4">
          <button type="submit" className="btn btn-primary btn-md" disabled={busy}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} {task ? 'Save changes' : 'Create task'}
          </button>
          <button type="button" className="btn btn-quiet btn-md" onClick={onClose}>Cancel</button>
        </footer>
      </form>
    </div>
  )
}

function Field({ label, hint, children }) {
  return (
    <label className="block">
      <span className="label mb-1.5 block">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-2xs text-ink3">{hint}</span>}
    </label>
  )
}
