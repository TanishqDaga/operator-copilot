import { Check, Crosshair, Droplets, Scale, SlidersHorizontal, Wrench } from 'lucide-react'
import ExplainPanel from '../components/ExplainPanel'
import ProximityGauge from '../components/ProximityGauge'
import SafetyBanner from '../components/SafetyBanner'
import { MachineControls, PersonControls } from '../components/SimControls'
import { Card, CardHeader, Chip, KV } from '../components/ui'
import { fmt } from '../lib/format'
import { useApp } from '../lib/store'
import Gate from './Gate'

export default function Safety() {
  return <Gate what="the live safety view"><SafetyView /></Gate>
}

function SafetyView() {
  const { state, meta } = useApp()
  const c = meta?.safety || {}
  const reasons = state?.safety?.reasons || []
  const p = state?.person || {}
  const rules = [
    { id: 'proximity-warn', label: `Distance < ${c.D_WARN} m or TTC < ${c.T_WARN} s`, result: 'WARNING', on: p.detected && (p.distance_m < c.D_WARN || p.ttc_s < c.T_WARN) },
    { id: 'proximity-crit', label: `Distance < ${c.D_CRIT} m or TTC < ${c.T_CRIT} s`, result: 'CRITICAL', on: p.detected && (p.distance_m < c.D_CRIT || p.ttc_s < c.T_CRIT) },
    { id: 'seatbelt', label: 'Moving (speed > 0) with seatbelt unfastened', result: 'WARNING', on: reasons.includes('seatbelt') },
    { id: 'wet', label: `Rain and travel speed > ${c.V_WET} km/h`, result: 'WARNING', on: reasons.includes('wet_ground') },
    { id: 'heat', label: `Heat → hydration notice every ${c.HYDRATION_EVERY_MIN} min`, result: 'NOTICE', on: state?.weather === 'heat' },
  ]
  return (
        <div className="space-y-5">
          <SafetyBanner state={state} variant="hero" />
          <div className="grid items-start gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader icon={Crosshair} title="Proximity" subtitle="Time-to-contact = distance ÷ closing speed"
                right={<Chip tone={p.source === 'camera' ? 'info' : 'default'}>Source: {p.source}</Chip>} />
              <div className="px-5 pb-5">
                <ProximityGauge person={p} constants={c} />
                <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Mini label="Distance" value={p.detected ? `${fmt(p.distance_m)} m` : '—'} />
                  <Mini label="Person approach" value={p.detected ? `${fmt(p.approach_ms, 2)} m/s` : '—'} />
                  <Mini label="Machine speed" value={`${fmt(state.speed_kmh / 3.6, 2)} m/s`} />
                  <Mini label="Time to contact" value={p.detected ? (p.ttc_s < 60 ? `${fmt(p.ttc_s)} s` : '> 60 s') : '—'} />
                </div>
              </div>
            </Card>
            <Card>
              <CardHeader icon={SlidersHorizontal} title="Person input" subtitle="Camera detection with slider fallback" />
              <div className="px-5 pb-5"><PersonControls /></div>
            </Card>
          </div>
          <div className="grid gap-5 xl:grid-cols-3">
            <Card>
              <CardHeader icon={Scale} title="Rules" subtitle="Deterministic — safety.py, never the LLM" />
              <ul className="space-y-2 px-5 pb-3">
                {rules.map((r) => (
                  <li key={r.id} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors duration-300 ${r.on ? (r.result === 'CRITICAL' ? 'border-crit/50 bg-crit-bg' : r.result === 'NOTICE' ? 'border-info/40 bg-info-bg' : 'border-warn/50 bg-warn-bg') : 'border-line bg-panel2'}`}>
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-md ${r.on ? 'bg-raised text-ink' : 'text-ink3'}`}>{r.on ? <Check size={14} strokeWidth={3} /> : <span className="h-1.5 w-1.5 rounded-full bg-line2" />}</span>
                    <span className={`flex-1 text-[13px] ${r.on ? 'text-ink' : 'text-ink2'}`}>{r.label}</span>
                    <span className={`text-2xs font-bold ${r.result === 'CRITICAL' ? 'text-crit' : r.result === 'NOTICE' ? 'text-info' : 'text-warn'}`}>{r.result}</span>
                  </li>
                ))}
              </ul>
              <div className="px-5 pb-5">
                <div className="label mb-1">Constants</div>
                <KV k="D_WARN / D_CRIT" v={`${c.D_WARN} m / ${c.D_CRIT} m`} />
                <KV k="T_WARN / T_CRIT" v={`${c.T_WARN} s / ${c.T_CRIT} s`} />
                <KV k="V_WET" v={`${c.V_WET} km/h`} />
                <KV k="Step-down hold" v={`${c.DOWNGRADE_HOLD_S} s`} />
              </div>
            </Card>
            <Card>
              <CardHeader icon={Wrench} title="Machine & site" subtitle="Seatbelt, travel and weather inputs" />
              <div className="px-5 pb-5">
                <div className="mb-4 grid grid-cols-3 gap-2">
                  <Mini label="Seatbelt" value={state.seatbelt ? 'Fastened' : 'Unfastened'} tone={state.seatbelt ? 'text-safe' : 'text-crit'} />
                  <Mini label="Speed" value={`${fmt(state.speed_kmh)} km/h`} />
                  <Mini label="Weather" value={state.weather[0].toUpperCase() + state.weather.slice(1)} tone={state.weather === 'rain' ? 'text-warn' : ''} />
                </div>
                <MachineControls only={['seatbelt', 'weather']} />
                {state.notices?.[0] && (
                  <div className="mt-4 flex items-center gap-2 rounded-xl border border-info/30 bg-info-bg px-3 py-2 text-sm text-info">
                    <Droplets size={16} /> {state.notices[0].text} <span className="num ml-auto text-2xs">{state.notices[0].ts}</span>
                  </div>
                )}
              </div>
            </Card>
            <ExplainPanel />
          </div>
        </div>
  )
}

function Mini({ label, value, tone = '' }) {
  return (
    <div className="rounded-xl border border-line bg-panel2 px-3 py-2.5">
      <div className="label">{label}</div>
      <div className={`num mt-1 text-lg font-semibold ${tone || 'text-ink'}`}>{value}</div>
    </div>
  )
}
