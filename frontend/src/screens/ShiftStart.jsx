import { ArrowRight, Check, ClipboardCheck, HardHat, Loader2, Lock, Power, Truck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, PageHeader, Progress, SyntheticTag } from '../components/ui'
import { api } from '../lib/api'
import { useApp } from '../lib/store'

export default function ShiftStart() {
  const { meta, state, refreshAll, session, schedule } = useApp()
  const nav = useNavigate()
  const [op, setOp] = useState(null)
  const [checked, setChecked] = useState({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const active = state?.shift?.active

  useEffect(() => { if (meta && !op) setOp(session?.role === 'operator' ? session.id : meta.default_operator) }, [meta, op, session])

  const items = meta?.checklist || []
  const groups = useMemo(() => items.reduce((g, c) => ({ ...g, [c.group]: [...(g[c.group] || []), c] }), {}), [items])
  const done = items.filter((c) => checked[c.id]).length
  const complete = items.length > 0 && done === items.length

  const start = async () => {
    setBusy(true); setErr(null)
    try {
      await api.post('/shift/start', { operator_id: op, checklist: checked })
      await refreshAll()
      nav('/dashboard')
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  if (active) {
    return (
      <div>
        <PageHeader title="Shift in progress" subtitle={`Started ${state.shift.started_at} · pre-start checklist completed`} />
        <Card className="p-8 text-center">
          <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-safe/15 text-safe"><Check size={30} /></span>
          <h2 className="mt-4 text-xl font-semibold">{state.shift.operator_name} is signed in on {state.machine_id}</h2>
          <p className="mt-1 text-ink3">All {items.length} pre-start items were confirmed before the machine was released.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button className="btn btn-primary btn-lg" onClick={() => nav('/dashboard')}>Go to dashboard <ArrowRight size={18} /></button>
            <button className="btn btn-ghost btn-lg" onClick={() => nav('/summary')}>End shift & handoff</button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title={state?.shift?.ended ? 'Start a new shift' : 'Start of shift'}
        subtitle="Sign in and complete the pre-start checklist. Tasks unlock once every item is confirmed."
        right={<SyntheticTag />}
      />
      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <div className="space-y-5">
          <Card>
            <CardHeader icon={HardHat} title="Operator" subtitle="Synthetic operator profiles" />
            <div className="space-y-2 px-3 pb-3">
              {meta?.operators?.map((o) => (
                <button key={o.id} onClick={() => setOp(o.id)}
                  className={`flex w-full items-center gap-3 rounded-xl border px-3 py-3 text-left transition-colors ${op === o.id ? 'border-cat/60 bg-cat/[0.07]' : 'border-transparent hover:bg-raised'}`}>
                  <span className={`grid h-10 w-10 place-items-center rounded-full text-sm font-bold ${op === o.id ? 'bg-cat text-cat-ink' : 'bg-raised text-ink2'}`}>
                    {o.name.split(' ').map((p) => p[0]).join('').replace('.', '')}
                  </span>
                  <span className="flex-1">
                    <span className="block text-sm font-semibold text-ink">{o.name}</span>
                    <span className="num block text-2xs text-ink3">{o.id} · {o.experience_yrs} yrs experience</span>
                  </span>
                  {op === o.id && <Check size={18} className="text-cat" />}
                </button>
              ))}
            </div>
          </Card>
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-cat text-cat-ink"><Truck size={20} /></span>
              <div>
                <div className="font-semibold text-ink">{meta?.machine_id}</div>
                <div className="text-2xs text-ink3">20-tonne class hydraulic excavator</div>
              </div>
            </div>
            <div className="mt-4 rounded-xl border border-line bg-panel2 p-3">
              <div className="label">Today's plan</div>
              <div className="mt-1 text-sm text-ink2">{meta?.plan}</div>
              {schedule?.published ? (
                <div className="mt-1 text-2xs text-ink2">
                  Published schedule <span className="num">{schedule.schedule_id}</span>: {schedule.tasks.length} task{schedule.tasks.length === 1 ? '' : 's'} for you
                  {schedule.tasks[0] ? <>, first <span className="num">{schedule.tasks[0].task_id}</span> at <span className="num">{schedule.tasks[0].start}</span></> : ''}
                </div>
              ) : schedule && <div className="mt-1 text-2xs text-ink3">No published schedule yet — the manager's original order will run.</div>}
              <div className="mt-2 flex items-center gap-1.5 text-2xs text-ink3"><Lock size={12} /> Task list and ETAs unlock after the checklist</div>
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader icon={ClipboardCheck} title="Pre-start checklist" subtitle="Tap each item once it has been physically checked"
            right={<span className="num text-sm font-semibold text-ink2">{done}/{items.length}</span>} />
          <div className="px-5"><Progress value={items.length ? done / items.length : 0} tone={complete ? 'safe' : 'cat'} /></div>
          <div className="space-y-5 px-5 py-5">
            {Object.entries(groups).map(([g, list]) => (
              <div key={g}>
                <div className="label mb-2">{g}</div>
                <div className="grid gap-2 md:grid-cols-2">
                  {list.map((c) => {
                    const on = !!checked[c.id]
                    return (
                      <button key={c.id} onClick={() => setChecked((x) => ({ ...x, [c.id]: !x[c.id] }))}
                        className={`flex min-h-[60px] items-center gap-3 rounded-xl border px-4 py-3 text-left transition-all ${on ? 'border-safe/50 bg-safe-bg' : 'border-line bg-panel2 hover:border-line2'}`}>
                        <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg border-2 transition-colors ${on ? 'border-safe bg-safe text-bg' : 'border-line2'}`}>
                          {on && <Check size={16} strokeWidth={3} />}
                        </span>
                        <span className={`text-sm ${on ? 'text-ink' : 'text-ink2'}`}>{c.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
            <button className="btn btn-primary btn-lg" disabled={!complete || !op || busy} onClick={start}>
              {busy ? <Loader2 size={18} className="animate-spin" /> : <Power size={18} />} Start shift
            </button>
            {!complete && <span className="text-sm text-ink3">{items.length - done} item{items.length - done === 1 ? '' : 's'} left before the machine is released</span>}
            <button className="btn btn-quiet btn-sm ml-auto" onClick={() => setChecked(Object.fromEntries(items.map((c) => [c.id, true])))}>
              Mark all checked (demo)
            </button>
            {err && <p className="w-full text-sm text-crit">{err}</p>}
          </div>
        </Card>
      </div>
    </div>
  )
}
