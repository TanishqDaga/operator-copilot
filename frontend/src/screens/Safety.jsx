import { Crosshair, Droplets, Wrench } from 'lucide-react'
import ExplainPanel from '../components/ExplainPanel'
import ProximityGauge from '../components/ProximityGauge'
import SafetyBanner from '../components/SafetyBanner'
import { Card, CardHeader, Chip } from '../components/ui'
import { fmt } from '../lib/format'
import { useApp } from '../lib/store'
import Gate from './Gate'

export default function Safety() {
  return <Gate what="the live safety view"><SafetyView /></Gate>
}

function SafetyView() {
  const { state, meta } = useApp()
  const c = meta?.safety || {}
  const p = state?.person || {}
  return (
        <div className="space-y-5">
          <SafetyBanner state={state} variant="hero" />
          <div className="grid gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader icon={Crosshair} title="Proximity"
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
              <CardHeader icon={Wrench} title="Machine & site" />
              <div className="px-5 pb-5">
                <div className="grid grid-cols-3 gap-2">
                  <Mini label="Seatbelt" value={state.seatbelt ? 'Fastened' : 'Unfastened'} tone={state.seatbelt ? 'text-safe' : 'text-crit'} />
                  <Mini label="Speed" value={`${fmt(state.speed_kmh)} km/h`} />
                  <Mini label="Weather" value={state.weather[0].toUpperCase() + state.weather.slice(1)} tone={state.weather === 'rain' ? 'text-warn' : ''} />
                </div>
                {state.notices?.[0] && (
                  <div className="mt-4 flex items-center gap-2 rounded-xl border border-info/30 bg-info-bg px-3 py-2 text-sm text-info">
                    <Droplets size={16} /> {state.notices[0].text} <span className="num ml-auto text-2xs">{state.notices[0].ts}</span>
                  </div>
                )}
              </div>
            </Card>
          </div>
          <ExplainPanel />
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
