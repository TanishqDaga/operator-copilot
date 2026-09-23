import { Cloud, CloudDrizzle, CloudFog, CloudRain, CloudSun, Database, Sun, Wind } from 'lucide-react'
import { CONDITION } from '../lib/format'
import { useApp } from '../lib/store'
import { Card, CardHeader } from './ui'

const ICON = { clear: Sun, cloudy: Cloud, rain: CloudRain, wind: Wind, low_visibility: CloudFog }
const CURRENT_ICON = { clear: CloudSun, rain: CloudDrizzle, heat: Sun }

export function SyntheticForecastTag() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-cat/30 bg-cat/10 px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wider text-cat">
      <Database size={11} /> Synthetic forecast
    </span>
  )
}

function rainBar(p) {
  return p >= 70 ? 'bg-info' : p >= 50 ? 'bg-info/75' : p >= 30 ? 'bg-info/45' : 'bg-info/25'
}

/** Hourly synthetic forecast strip. `onScenario` (manager only) switches the demo scenario. */
export default function WeatherForecast({ forecast, scenarios, onScenario, busy, compact = false }) {
  const { state } = useApp()
  if (!forecast) return null
  const inWindow = (h) => forecast.windows.filter((w) => h.start_min >= w.start_min && h.start_min < w.end_min).map((w) => w.kind)
  const current = state?.shift?.active ? state.weather : null
  const CurIcon = CURRENT_ICON[current] || CloudSun
  return (
    <Card>
      <CardHeader icon={CloudRain} title="Weather forecast" subtitle={forecast.summary}
        right={
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <SyntheticForecastTag />
            {onScenario && (
              <select className="h-8 rounded-lg border border-line2 bg-panel2 px-2 text-xs text-ink disabled:opacity-50"
                value={forecast.scenario} disabled={busy} aria-label="Forecast scenario (demo)"
                onChange={(e) => onScenario(e.target.value)}>
                {scenarios?.map((s) => <option key={s.value} value={s.value}>Scenario: {s.label}</option>)}
              </select>
            )}
          </div>
        } />
      <div className="overflow-x-auto px-5">
        <div className="grid min-w-[640px] gap-1.5" style={{ gridTemplateColumns: `repeat(${forecast.hours.length}, minmax(0, 1fr))` }}>
          {forecast.hours.map((h) => {
            const Icon = ICON[h.condition] || Cloud
            const hz = inWindow(h)
            const c = CONDITION[h.condition] || CONDITION.cloudy
            return (
              <div key={h.time} title={`${h.time}–${h.end} · ${c.label} · ${h.rain_probability}% rain · ${h.wind_kmh} km/h · ${h.visibility_m} m`}
                className={`flex flex-col items-center rounded-xl border px-1 py-2 text-center ${hz.length ? 'border-info/40 bg-info-bg/60' : 'border-line bg-panel2'}`}>
                <span className="num text-xs font-semibold text-ink">{h.time}</span>
                <Icon size={18} className={`mt-1.5 ${c.tone}`} />
                <span className={`mt-1 text-2xs font-semibold uppercase tracking-wide ${c.tone}`}>{c.label}</span>
                {!compact && (
                  <div className="mt-2 flex h-12 w-3 items-end overflow-hidden rounded-full bg-line" aria-hidden>
                    <div className={`w-full rounded-full ${rainBar(h.rain_probability)}`} style={{ height: `${h.rain_probability}%` }} />
                  </div>
                )}
                <span className="num mt-1 text-sm font-semibold text-ink">{h.rain_probability}%</span>
                <span className={`num text-2xs ${h.wind_kmh >= 35 ? 'text-warn' : 'text-ink3'}`}>{h.wind_kmh} km/h</span>
                <span className={`num text-2xs ${h.visibility_m < 1000 ? 'text-anom' : 'text-ink3'}`}>
                  {h.visibility_m >= 1000 ? `${(h.visibility_m / 1000).toFixed(1)} km` : `${h.visibility_m} m`}
                </span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 pt-3 text-2xs text-ink3">
        <span>Rain probability · wind · visibility per hour</span>
        {forecast.windows.map((w) => (
          <span key={`${w.kind}-${w.start}`} className="num rounded-md border border-info/30 bg-info-bg px-1.5 py-0.5 text-info">
            {w.kind === 'rain' ? 'Rain' : w.kind === 'wind' ? 'Wind' : 'Low vis.'} {w.start}–{w.end}
          </span>
        ))}
        <span className="ml-auto inline-flex items-center gap-1.5">
          <CurIcon size={13} /> Current (in cab): <span className="text-ink2">{current || 'shift not started'}</span>
        </span>
      </div>
    </Card>
  )
}
