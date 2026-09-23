import { Footprints, Truck } from 'lucide-react'
import { fmt } from '../lib/format'

const MAX_M = 20

/** Linear distance scale with the rule-engine zones drawn from the live constants. */
export default function ProximityGauge({ person, constants }) {
  const dWarn = constants?.D_WARN ?? 8
  const dCrit = constants?.D_CRIT ?? 4
  const d = person?.detected ? Math.min(person.distance_m, MAX_M) : null
  const pct = (m) => `${(m / MAX_M) * 100}%`
  const tone = d === null ? 'text-ink3' : d < dCrit ? 'text-crit' : d < dWarn ? 'text-warn' : 'text-safe'

  return (
    <div>
      <div className="relative h-16 rounded-xl border border-line bg-panel2 overflow-hidden">
        <div className="absolute inset-y-0 left-0 bg-crit/20" style={{ width: pct(dCrit) }} />
        <div className="absolute inset-y-0 bg-warn/15" style={{ left: pct(dCrit), width: pct(dWarn - dCrit) }} />
        <div className="absolute inset-y-0 bg-safe/[0.07]" style={{ left: pct(dWarn), right: 0 }} />
        <div className="absolute inset-y-0 w-px bg-crit/70" style={{ left: pct(dCrit) }} />
        <div className="absolute inset-y-0 w-px bg-warn/70" style={{ left: pct(dWarn) }} />
        <div className="absolute left-2 top-1/2 -translate-y-1/2 grid h-10 w-10 place-items-center rounded-lg bg-cat text-cat-ink">
          <Truck size={20} />
        </div>
        {d !== null && (
          <div className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 transition-[left] duration-700 ease-out ${tone}`} style={{ left: `max(3.5rem, ${pct(d)})` }}>
            <div className="grid h-10 w-10 place-items-center rounded-full border-2 border-current bg-bg">
              <Footprints size={18} />
            </div>
          </div>
        )}
      </div>
      <div className="relative mt-1.5 h-4 text-2xs text-ink3 num">
        <span className="absolute left-0">0 m</span>
        <span className="absolute -translate-x-1/2 text-crit" style={{ left: pct(dCrit) }}>{dCrit} m</span>
        <span className="absolute -translate-x-1/2 text-warn" style={{ left: pct(dWarn) }}>{dWarn} m</span>
        <span className="absolute right-0">{MAX_M}+ m</span>
      </div>
      <div className="mt-2 text-xs text-ink3">
        {d === null ? 'No person in range.' : <>Person at <span className={`num font-semibold ${tone}`}>{fmt(person.distance_m)} m</span>, approaching at <span className="num text-ink2">{fmt(person.approach_ms, 2)} m/s</span>.</>}
      </div>
    </div>
  )
}
