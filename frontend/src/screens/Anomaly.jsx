import { Activity, FlaskConical, ShieldCheck, Table2 } from 'lucide-react'
import { AnomalyDetail } from '../components/AnomalyCard'
import EventList from '../components/EventList'
import { MachineControls } from '../components/SimControls'
import { Card, CardHeader, PageHeader, Source, SyntheticTag } from '../components/ui'
import { fmt } from '../lib/format'
import { useApp } from '../lib/store'
import Gate from './Gate'

const FEATURES = [
  ['idle_min', 'Idle duration', 'min'], ['rpm', 'Engine speed', 'rpm'], ['cycle_s', 'Cycle time', 's'],
  ['hyd_temp', 'Hydraulic oil temp', '°C'], ['fuel_rate_lph', 'Fuel burn rate', 'L/h'], ['payload_t', 'Bucket payload', 't'],
]

export default function Anomaly() {
  return <Gate what="anomaly detection"><AnomalyView /></Gate>
}

function AnomalyView() {
  const { state, events, meta } = useApp()
  const a = state?.anomaly
  const anomEvents = events.filter((e) => e.kind === 'anomaly')
  return (
        <div className="space-y-5">
          <PageHeader title="Anomaly detection" subtitle="Is this machine behaving unlike this operator's normal? The model flags it; it does not diagnose it." />
          {a?.flag ? <AnomalyDetail /> : (
            <Card className="p-6">
              <div className="flex items-center gap-4">
                <span className="grid h-14 w-14 place-items-center rounded-2xl bg-safe/15 text-safe"><ShieldCheck size={28} /></span>
                <div>
                  <div className="text-xl font-semibold text-ink">No anomaly — within your normal pattern</div>
                  <p className="mt-1 text-sm text-ink3">
                    Live score <span className="num text-ink2">{fmt(a?.score, 3)}</span> vs flag threshold <span className="num text-ink2">{fmt(a?.threshold, 3)}</span> on the {a?.model_state} model.
                    Lower scores are less typical.
                  </p>
                </div>
              </div>
            </Card>
          )}
          <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
            <Card>
              <CardHeader icon={Table2} title="Live features vs your baseline" subtitle={`${state.operator_id} · ${state.idle ? 'idle' : 'working'} samples`} />
              <FeatureTable />
              <Source className="px-5 py-4">
                IsolationForest (one per machine state) trained on {meta?.anomaly?.n_train?.working?.toLocaleString()} working and {meta?.anomaly?.n_train?.idle?.toLocaleString()} idle
                historical samples (synthetic). Flags when the score stays below the least-typical {Math.round((meta?.anomaly?.score_quantile ?? 0.05) * 100)}% of normal data for {meta?.anomaly?.persist_ticks} s.
              </Source>
            </Card>
            <div className="space-y-5">
              <Card>
                <CardHeader icon={FlaskConical} title="Simulate" subtitle="Inject an idle stretch" right={<SyntheticTag />} />
                <div className="px-5 pb-5"><MachineControls only={['idle']} /></div>
              </Card>
              <Card>
                <CardHeader icon={Activity} title="This shift" subtitle={`${anomEvents.filter((e) => e.level === 'ANOMALY').length} anomalies flagged`} />
                <EventList events={anomEvents} compact />
              </Card>
            </div>
          </div>
        </div>
  )
}

function FeatureTable() {
  const { state } = useApp()
  const b = state?.baseline_snapshot
  const a = state.anomaly
  const live = {
    idle_min: state.idle_min, rpm: state.rpm, cycle_s: state.cycle_s, hyd_temp: state.hyd_temp,
    fuel_rate_lph: state.fuel_rate_lph, payload_t: state.payload_t,
  }
  return (
    <div className="overflow-x-auto px-5">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left label">
            <th className="py-2 font-semibold">Feature</th>
            <th className="py-2 text-right font-semibold">Now</th>
            <th className="py-2 text-right font-semibold">Your median</th>
            <th className="py-2 text-right font-semibold">Your usual range</th>
          </tr>
        </thead>
        <tbody>
          {FEATURES.map(([k, label, unit]) => {
            const base = b?.[k]
            const flagged = a?.flag && a.feature === k
            const out = base && (live[k] < base.q25 - 1.5 * (base.q75 - base.q25) || live[k] > base.q75 + 1.5 * (base.q75 - base.q25))
            return (
              <tr key={k} className={`border-t border-line ${flagged ? 'bg-anom-bg' : ''}`}>
                <td className="py-2.5 text-ink2">{label}</td>
                <td className={`num py-2.5 text-right ${flagged ? 'font-semibold text-anom' : out ? 'text-warn' : 'text-ink'}`}>{fmt(live[k])} <span className="text-ink3">{unit}</span></td>
                <td className="num py-2.5 text-right text-ink2">{base ? fmt(base.median) : '—'}</td>
                <td className="num py-2.5 text-right text-ink3">{base ? `${fmt(base.q25)}–${fmt(base.q75)}` : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
