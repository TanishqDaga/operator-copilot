import { Activity, CircleHelp, Fuel } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ANOMALY_LABEL, fmt } from '../lib/format'
import { useApp } from '../lib/store'
import { Card, CardHeader, Chip } from './ui'

export function BaselineScale({ current, median, q25, q75, unit }) {
  const lo = Math.min(0, current, q25)
  const hi = Math.max(current, q75) * 1.25 || 1
  const pct = (v) => `${((v - lo) / (hi - lo)) * 100}%`
  return (
    <div>
      <div className="relative h-12">
        <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-line" />
        <div className="absolute top-1/2 h-4 -translate-y-1/2 rounded-md bg-safe/25 border border-safe/40" style={{ left: pct(q25), width: `calc(${pct(q75)} - ${pct(q25)})` }} />
        <div className="absolute top-1/2 h-6 w-0.5 -translate-y-1/2 bg-safe" style={{ left: pct(median) }} />
        <div className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 transition-[left] duration-700" style={{ left: pct(current) }}>
          <div className="h-8 w-8 rounded-full border-[3px] border-anom bg-bg shadow-[0_0_0_4px_rgba(179,140,255,0.15)]" />
        </div>
      </div>
      <div className="relative h-8 text-2xs num">
        <span className="absolute -translate-x-1/2 text-safe whitespace-nowrap" style={{ left: pct(median) }}>usual {fmt(median)} {unit}</span>
        <span className="absolute top-4 -translate-x-1/2 text-anom font-semibold whitespace-nowrap" style={{ left: pct(current) }}>now {fmt(current)} {unit}</span>
      </div>
    </div>
  )
}

export function AnomalyCompact() {
  const { state } = useApp()
  const a = state?.anomaly
  return (
    <Card className={a?.flag ? 'border-anom/40' : ''}>
      <CardHeader icon={Activity} title="Anomaly watch" subtitle="IsolationForest vs. your own baseline"
        right={<Link to="/anomaly" className="text-xs font-semibold text-ink3 hover:text-cat">Details →</Link>} />
      <div className="px-5 pb-5">
        {a?.flag ? (
          <div className="animate-rise">
            <Chip tone="anom">{ANOMALY_LABEL[a.type] || a.type}</Chip>
            <div className="mt-3 flex items-baseline gap-3">
              <span className="num text-4xl font-bold text-anom">{fmt(a.current)}</span>
              <span className="text-sm text-ink3">{a.unit} now vs your usual <span className="num text-ink">{fmt(a.baseline)} {a.unit}</span></span>
            </div>
            <p className="mt-2 text-[13px] text-ink3">Possible causes: {a.possible_causes.slice(0, 2).join(', ').toLowerCase()}…</p>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-2 text-safe"><span className="h-2 w-2 rounded-full bg-safe" /><span className="text-sm font-semibold">Within your normal pattern</span></div>
            <p className="mt-2 text-[13px] text-ink3">
              Model score <span className="num text-ink2">{fmt(a?.score, 3)}</span> vs flag threshold <span className="num text-ink2">{fmt(a?.threshold, 3)}</span> ({a?.model_state} model).
            </p>
          </div>
        )}
      </div>
    </Card>
  )
}

export function AnomalyDetail() {
  const { state } = useApp()
  const a = state?.anomaly
  if (!a?.flag) return null
  return (
    <Card className="overflow-hidden border-anom/40">
      <div className="h-1 bg-gradient-to-r from-anom via-anom/40 to-transparent" />
      <CardHeader icon={Activity} title={`${a.label} unusual`} subtitle={`Flagged since ${a.since} · ${ANOMALY_LABEL[a.type] || a.type}`}
        right={<Chip tone="anom">Anomaly</Chip>} />
      <div className="grid gap-6 px-5 pb-5 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <div className="grid grid-cols-3 gap-3">
            <Big label="Current" value={fmt(a.current)} unit={a.unit} tone="text-anom" />
            <Big label="Your usual (median)" value={fmt(a.baseline)} unit={a.unit} tone="text-safe" />
            <Big label="Your usual range" value={`${fmt(a.baseline_q25)}–${fmt(a.baseline_q75)}`} unit={a.unit} tone="text-ink" />
          </div>
          <div className="mt-6"><BaselineScale current={a.current} median={a.baseline} q25={a.baseline_q25} q75={a.baseline_q75} unit={a.unit} /></div>
        </div>
        <div className="space-y-4">
          <div className="rounded-xl border border-line bg-panel2 p-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-ink"><CircleHelp size={16} className="text-anom" /> Possible causes</div>
            <p className="mt-1 text-2xs text-ink3">The model detects that the pattern is unusual — it cannot know why. Check these:</p>
            <ul className="mt-3 space-y-2">
              {a.possible_causes.map((c) => (
                <li key={c} className="flex items-start gap-2.5 text-sm text-ink2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-anom" /> {c}
                </li>
              ))}
            </ul>
          </div>
          {a.type === 'excess_idle' && a.idle_fuel_l != null && (
            <div className="rounded-xl border border-line bg-panel2 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-ink"><Fuel size={16} className="text-cat" /> Fuel burned while idle</div>
              <div className="mt-2 num text-2xl font-semibold text-ink">{fmt(a.idle_fuel_l)} L</div>
            </div>
          )}
        </div>
      </div>
    </Card>
  )
}

function Big({ label, value, unit, tone }) {
  return (
    <div className="rounded-xl border border-line bg-panel2 px-4 py-3">
      <div className="label">{label}</div>
      <div className={`mt-1.5 num text-2xl font-semibold ${tone}`}>{value} <span className="text-xs text-ink3">{unit}</span></div>
    </div>
  )
}
