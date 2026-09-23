import { OctagonAlert, ShieldCheck, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { REASON_LABEL, fmt } from '../lib/format'

const STYLE = {
  SAFE: {
    icon: ShieldCheck, wrap: 'border-safe/30 bg-gradient-to-r from-safe-bg via-panel to-panel', accent: 'bg-safe',
    text: 'text-safe', iconBox: 'bg-safe/15 text-safe', headline: 'All safety rules clear',
  },
  WARNING: {
    icon: TriangleAlert, wrap: 'border-warn/50 bg-gradient-to-r from-warn-bg via-[#1a130b] to-panel', accent: 'bg-warn',
    text: 'text-warn', iconBox: 'bg-warn/15 text-warn', headline: 'Caution — rule threshold crossed',
  },
  CRITICAL: {
    icon: OctagonAlert, wrap: 'border-crit/70 bg-gradient-to-r from-crit-bg via-[#1f0b0c] to-panel', accent: 'bg-crit',
    text: 'text-crit', iconBox: 'bg-crit text-white animate-pulseRing', headline: 'Stop — critical safety rule',
  },
}

export default function SafetyBanner({ state, variant = 'hero', meta }) {
  const s = state?.safety || { level: 'SAFE', reasons: [], details: [] }
  const st = STYLE[s.level] || STYLE.SAFE
  const Icon = st.icon
  const p = state?.person || {}
  const hero = variant === 'hero'

  return (
    <section className={`relative overflow-hidden rounded-2xl border ${st.wrap} shadow-card transition-colors duration-500`}>
      <div className={`absolute inset-y-0 left-0 w-1.5 ${st.accent} transition-colors duration-500 ${s.level === 'CRITICAL' ? 'animate-critGlow' : ''}`} />
      <div className={`flex flex-col gap-5 ${hero ? 'p-6 md:p-7 lg:flex-row lg:items-center' : 'p-5 md:flex-row md:items-center'}`}>
        <div key={s.level} className={`flex items-center gap-5 animate-rise ${hero ? 'lg:w-[400px] shrink-0' : 'md:w-[300px] shrink-0'}`}>
          <span className={`grid shrink-0 place-items-center rounded-2xl ${st.iconBox} ${hero ? 'h-20 w-20' : 'h-14 w-14'} transition-colors`}>
            <Icon size={hero ? 40 : 28} strokeWidth={2.2} />
          </span>
          <div className="min-w-0">
            <div className="label">Safety level · rule engine</div>
            <div className={`font-extrabold tracking-tight ${st.text} ${hero ? 'text-5xl 2xl:text-6xl' : 'text-3xl'} leading-none mt-1`}>{s.level}</div>
            <div className="mt-2 text-sm text-ink2">{st.headline}</div>
          </div>
        </div>

        <div className="min-w-0 flex-1">
          {s.reasons.length ? (
            <ul className="space-y-2">
              {s.details.map((d, i) => (
                <li key={s.reasons[i] || i} className="flex items-start gap-3 animate-rise">
                  <span className={`mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 text-2xs font-bold uppercase tracking-wider ${st.text} border border-current/30 bg-black/20`}>
                    {REASON_LABEL[s.reasons[i]] || s.reasons[i]}
                  </span>
                  <span className={`text-ink ${hero ? 'text-base' : 'text-sm'}`}>{d}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-ink2">
              Monitoring proximity (&lt; {meta?.safety?.D_WARN ?? 8} m / TTC &lt; {meta?.safety?.T_WARN ?? 4} s), seatbelt while moving,
              wet-ground travel speed and heat. No rule is active.
            </p>
          )}
          {!hero && (
            <Link to="/safety" className="mt-3 inline-flex text-xs font-semibold text-ink3 hover:text-cat">Open safety view →</Link>
          )}
        </div>

        <div className="flex shrink-0 gap-3">
          <Metric label="Person" value={p.detected ? fmt(p.distance_m) : '—'} unit={p.detected ? 'm' : ''} sub={p.detected ? `via ${p.source}` : 'none detected'} hero={hero} />
          <Metric label="Time to contact" value={p.detected && p.ttc_s < 60 ? fmt(p.ttc_s) : '—'} unit={p.detected && p.ttc_s < 60 ? 's' : ''}
            sub={p.detected ? `${fmt(p.closing_ms, 2)} m/s closing` : 'no approach'} hero={hero} />
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value, unit, sub, hero }) {
  return (
    <div className={`rounded-xl border border-line2 bg-black/25 px-4 py-3 ${hero ? 'min-w-[132px]' : 'min-w-[112px]'}`}>
      <div className="label">{label}</div>
      <div className="mt-1 flex items-baseline gap-1">
        <span className={`num font-semibold text-ink ${hero ? 'text-3xl' : 'text-2xl'}`}>{value}</span>
        <span className="text-xs text-ink3">{unit}</span>
      </div>
      <div className="mt-0.5 text-2xs text-ink3">{sub}</div>
    </div>
  )
}
