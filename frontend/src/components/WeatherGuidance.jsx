import { CloudRain, CloudSun, Sun } from 'lucide-react'

const CURRENT = { clear: CloudSun, rain: CloudRain, heat: Sun }

/** Weather ahead for the operator's current and next tasks (forecast is synthetic). */
export default function WeatherGuidance({ weather }) {
  if (!weather) return null
  const Icon = CURRENT[weather.current] || CloudSun
  const t = weather.trend
  return (
    <div className="rounded-xl border border-line bg-panel2 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="label flex items-center gap-1.5"><CloudRain size={12} /> Weather ahead</div>
        {weather.current && <span className="inline-flex items-center gap-1 text-2xs text-ink3"><Icon size={12} /> now: <span className="text-ink2">{weather.current}</span></span>}
      </div>
      {t && (
        <div className="mt-2">
          <div className="text-2xs text-ink3">Rain probability{weather.schedule_now ? ` (schedule clock ${weather.schedule_now})` : ''}</div>
          <div className="num mt-0.5 text-xl font-semibold text-ink">
            {t.now_pct}% {t.rising && <span className="text-info">→ {t.peak_pct}%</span>}
            {t.rising && <span className="ml-1 text-xs font-normal text-ink3">at {t.peak_at}</span>}
          </div>
        </div>
      )}
      <ul className="mt-3 space-y-2">
        {weather.items.map((i) => (
          <li key={i.action} className="text-[13px] leading-5">
            <span className="text-ink">{i.action}</span>
            <span className="block text-2xs text-ink3">{i.reason}</span>
          </li>
        ))}
        {!weather.items.length && <li className="text-[13px] text-ink3">{t?.text}.</li>}
      </ul>
      <p className="mt-3 text-2xs text-ink3">Synthetic forecast · {weather.forecast_summary}</p>
    </div>
  )
}
