import { ArrowDown, ArrowUp, CloudRain, Eye, Lock, Pin, Wind } from 'lucide-react'
import { SENS_TONE, moveTone } from '../lib/format'
import { Chip } from './ui'

const FACTOR_ICON = { rain: CloudRain, wind: Wind, visibility: Eye }
const LEVEL_SHORT = { low: 'Low', medium: 'Med', high: 'High' }

/** Three small pills: rain / wind / visibility sensitivity. */
export function SensitivityChips({ profile, className = '' }) {
  if (!profile) return null
  return (
    <span className={`inline-flex flex-wrap gap-1 ${className}`}>
      {['rain', 'wind', 'visibility'].map((f) => {
        const Icon = FACTOR_ICON[f]
        const tone = { low: 'border-safe/30 text-safe', medium: 'border-warn/40 text-warn', high: 'border-crit/50 text-crit' }[profile[f]]
        return (
          <span key={f} title={`${f} sensitivity: ${profile[f]}`}
            className={`inline-flex items-center gap-1 rounded-md border bg-black/20 px-1.5 py-0.5 text-2xs font-semibold ${tone}`}>
            <Icon size={11} /> {LEVEL_SHORT[profile[f]]}
          </span>
        )
      })}
    </span>
  )
}

/** Estimated weather impact of the task in its scheduled window. */
export default function WeatherImpactBadge({ impact, className = '' }) {
  if (!impact) return null
  return <Chip tone={SENS_TONE[impact]} className={className}>{impact} weather impact</Chip>
}

/** "Moved earlier — rain sensitive", "Manager override", … */
export function MoveBadge({ rec, className = '' }) {
  if (!rec) return null
  const Icon = rec.source === 'manager_override' ? Pin : rec.source === 'locked' ? Lock
    : rec.moved === 'earlier' ? ArrowUp : rec.moved === 'later' ? ArrowDown : null
  return (
    <Chip tone={moveTone(rec)} className={className}>
      {Icon && <Icon size={12} />} {rec.label}
    </Chip>
  )
}
