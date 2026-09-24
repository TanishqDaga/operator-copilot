import { Gauge, Lightbulb } from 'lucide-react'
import { hm } from '../lib/format'
import { Card, CardHeader } from './ui'

function Metric({ label, value, sub, tone = 'text-ink' }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2">
      <div className="text-2xs text-ink3">{label}</div>
      <div className={`num text-base font-semibold ${tone}`}>{value}</div>
      {sub && <div className="num text-2xs text-ink3">{sub}</div>}
    </div>
  )
}

function Effic({ c }) {
  if (!c || c.status !== 'ok') return { value: 'Collecting data', sub: c ? `${c.n}/${c.needed} cycles` : null, tone: 'text-ink3' }
  const e = c.efficiency_pct
  return { value: `${e > 0 ? '+' : ''}${e.toFixed(0)}%`, sub: `${c.current_s} s vs ${c.baseline_s} s`, tone: e >= 0 ? 'text-safe' : 'text-warn' }
}

/** Live productivity for the current shift — operational facts, shown as "Collecting data" until meaningful. */
export default function ProductivityMetrics({ p }) {
  const t = p?.time
  const ok = t && t.status === 'ok'
  const ce = Effic({ c: p?.cycle })
  return (
    <div className="rounded-xl border border-line bg-panel2 p-4">
      <div className="label flex items-center gap-1.5"><Gauge size={12} /> Productivity · this shift</div>
      {!t ? <p className="mt-2 text-sm text-ink3">{p?.note}</p> : (
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Metric label="Utilisation" value={ok ? `${t.utilization_pct}%` : 'Collecting data'} tone={ok ? 'text-ink' : 'text-ink3'}
            sub={ok ? `active ${hm(t.active_min)} of ${hm(t.elapsed_min)}` : null} />
          <Metric label="Idle today" value={hm(t.idle_min)} tone={t.idle_min >= 5 ? 'text-anom' : 'text-ink'} sub={`travel ${hm(t.travel_min)}`} />
          <Metric label="Cycle vs your baseline" value={ce.value} sub={ce.sub} tone={ce.tone} />
          <Metric label="Tasks completed" value={`${p.tasks_completed} / ${p.tasks_total}`} sub="your assigned tasks" />
        </div>
      )}
      <p className="mt-2 text-2xs text-ink3">Operational metrics from machine telemetry — not a rating of the operator.</p>
    </div>
  )
}

/** End-of-shift roll-up for the Summary screen. */
export function OperatorProductivitySummary({ s }) {
  if (!s?.available) return null
  const t = s.time
  const c = s.cycle
  return (
    <Card>
      <CardHeader icon={Gauge} title="Operator productivity" subtitle="This shift's execution of the published schedule" />
      <div className="grid grid-cols-2 gap-2 px-5 md:grid-cols-4 xl:grid-cols-5">
        <Metric label="Tasks completed" value={s.tasks_completed} sub={`of ${s.tasks_scheduled} scheduled`} />
        <Metric label="Active time" value={hm(t.active_min)} sub={t.status === 'ok' ? `${t.utilization_pct}% utilisation` : 'collecting data'} />
        <Metric label="Idle time" value={hm(t.idle_min)} sub={`travel ${hm(t.travel_min)}`} />
        <Metric label="Average cycle" value={c.status === 'ok' ? `${c.current_s} s` : 'Collecting data'} sub={c.status === 'ok' ? `baseline ${c.baseline_s} s` : `${c.n}/${c.needed} cycles`} />
        <Metric label="Cycle vs baseline" value={c.status === 'ok' ? `${c.efficiency_pct > 0 ? '+' : ''}${c.efficiency_pct.toFixed(0)}%` : '—'}
          tone={c.status === 'ok' ? (c.efficiency_pct >= 0 ? 'text-safe' : 'text-warn') : 'text-ink3'} sub="shorter cycles = +" />
        <Metric label="Schedule adherence" value={s.schedule_adherence_pct != null ? `${s.schedule_adherence_pct}%` : '—'} sub="see note below" />
        <Metric label="Weather disruptions" value={s.weather_disruptions} sub="changes to rain / heat" />
        <Metric label="Productivity opportunities" value={s.opportunities.length} />
      </div>
      <div className="px-5 pt-4">
        <div className="label mb-2 flex items-center gap-1.5"><Lightbulb size={12} /> Productivity opportunities</div>
        {s.opportunities.length ? (
          <ul className="space-y-1.5">
            {s.opportunities.map((o) => <li key={o} className="rounded-lg border border-line bg-panel2 px-3 py-2 text-sm text-ink2">{o}</li>)}
          </ul>
        ) : <p className="text-sm text-ink3">No notable observations this shift.</p>}
      </div>
    </Card>
  )
}
