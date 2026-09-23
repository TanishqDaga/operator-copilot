import { Database, Info } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { LEVEL } from '../lib/format'

export function Card({ className = '', children, ...rest }) {
  return <section className={`card ${className}`} {...rest}>{children}</section>
}

export function CardHeader({ icon: Icon, title, subtitle, right, className = '' }) {
  return (
    <header className={`flex items-start justify-between gap-3 px-5 pt-4 pb-3 ${className}`}>
      <div className="flex items-center gap-3 min-w-0">
        {Icon && (
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-raised border border-line2 text-ink2">
            <Icon size={16} strokeWidth={2} />
          </span>
        )}
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold leading-tight text-ink truncate">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[13px] text-ink3 truncate">{subtitle}</p>}
        </div>
      </div>
      {right}
    </header>
  )
}

/** "Where does this number come from" — shown under every card that displays a computed value. */
export function Source({ children, className = '' }) {
  return (
    <p className={`flex items-start gap-1.5 text-2xs leading-[16px] text-ink3 ${className}`}>
      <Info size={12} className="mt-[2px] shrink-0" />
      <span>{children}</span>
    </p>
  )
}

export function SyntheticTag({ className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border border-cat/30 bg-cat/10 px-1.5 py-0.5 text-2xs font-semibold uppercase tracking-wider text-cat ${className}`}>
      <Database size={11} /> Synthetic
    </span>
  )
}

export function LevelPill({ level, size = 'md', pulse = true }) {
  const l = LEVEL[level] || LEVEL.INFO
  const sz = size === 'lg' ? 'h-9 px-3.5 text-sm' : size === 'sm' ? 'h-6 px-2 text-2xs' : 'h-7 px-2.5 text-xs'
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border ${l.border} ${l.soft} ${l.text} ${sz} font-bold uppercase tracking-wider transition-colors duration-300`}>
      <span className="relative flex h-2 w-2">
        {pulse && level === 'CRITICAL' && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${l.bg} opacity-75`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${l.bg}`} />
      </span>
      {level}
    </span>
  )
}

export function Chip({ children, tone = 'default', className = '' }) {
  const tones = {
    default: 'border-line2 bg-raised text-ink2',
    warn: 'border-warn/40 bg-warn-bg text-warn',
    crit: 'border-crit/50 bg-crit-bg text-crit',
    safe: 'border-safe/40 bg-safe-bg text-safe',
    anom: 'border-anom/40 bg-anom-bg text-anom',
    info: 'border-info/30 bg-info-bg text-info',
    cat: 'border-cat/40 bg-cat/10 text-cat',
  }
  return <span className={`inline-flex items-center gap-1.5 rounded-lg border px-2 py-1 text-xs font-medium ${tones[tone]} ${className}`}>{children}</span>
}

/** A number that briefly highlights whenever its value changes. */
export function Live({ value, className = '' }) {
  const prev = useRef(value)
  const [k, setK] = useState(0)
  useEffect(() => {
    if (prev.current !== value) { setK((x) => x + 1); prev.current = value }
  }, [value])
  return <span key={k} className={`num rounded-md ${k ? 'animate-flash' : ''} ${className}`}>{value}</span>
}

export function Stat({ icon: Icon, label, value, unit, sub, tone, flash = false, className = '' }) {
  const toneCls = tone === 'warn' ? 'text-warn' : tone === 'crit' ? 'text-crit' : tone === 'safe' ? 'text-safe' : tone === 'anom' ? 'text-anom' : 'text-ink'
  return (
    <div className={`rounded-xl border border-line bg-panel2 px-4 py-3 ${className}`}>
      <div className="flex items-center gap-1.5 label">
        {Icon && <Icon size={13} />} {label}
      </div>
      <div className={`mt-1.5 flex items-baseline gap-1 ${toneCls}`}>
        {flash ? <Live value={value} className="text-[22px] font-semibold leading-none" />
          : <span className="num text-[22px] font-semibold leading-none">{value}</span>}
        {unit && <span className="text-xs text-ink3">{unit}</span>}
      </div>
      {sub && <div className="mt-1 text-2xs text-ink3 truncate">{sub}</div>}
    </div>
  )
}

export function Progress({ value, tone = 'cat', className = '' }) {
  const bg = { cat: 'bg-cat', safe: 'bg-safe', warn: 'bg-warn', info: 'bg-info' }[tone]
  return (
    <div className={`h-2 w-full overflow-hidden rounded-full bg-line ${className}`}>
      <div className={`h-full rounded-full ${bg} transition-[width] duration-700 ease-out`} style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }} />
    </div>
  )
}

export function Segmented({ options, value, onChange, size = 'md' }) {
  const h = size === 'lg' ? 'h-12 text-sm' : 'h-10 text-[13px]'
  return (
    <div className="inline-flex w-full rounded-xl border border-line2 bg-panel2 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          disabled={o.disabled}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-3 font-semibold transition-all ${h} disabled:opacity-40 ${
            value === o.value ? 'bg-raised text-ink shadow-[0_0_0_1px_#2E3540]' : 'text-ink3 hover:text-ink2'
          }`}
        >
          {o.icon && <o.icon size={15} />} {o.label}
        </button>
      ))}
    </div>
  )
}

export function Toggle({ checked, onChange, label, sub, tone = 'safe' }) {
  const on = tone === 'crit' ? 'bg-crit' : tone === 'warn' ? 'bg-warn' : 'bg-safe'
  return (
    <button type="button" onClick={() => onChange(!checked)} className="flex w-full items-center justify-between gap-4 rounded-xl border border-line bg-panel2 px-4 py-3 text-left hover:border-line2">
      <div>
        <div className="text-sm font-semibold text-ink">{label}</div>
        {sub && <div className="text-2xs text-ink3">{sub}</div>}
      </div>
      <span className={`relative h-7 w-12 shrink-0 rounded-full transition-colors ${checked ? on : 'bg-line2'}`}>
        <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${checked ? 'left-6' : 'left-1'}`} />
      </span>
    </button>
  )
}

export function Empty({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      {Icon && (
        <span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl border border-line2 bg-raised text-ink3">
          <Icon size={24} />
        </span>
      )}
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      {children && <p className="mt-1.5 max-w-md text-sm text-ink3">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, right }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-[22px] font-bold tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink3">{subtitle}</p>}
      </div>
      {right}
    </div>
  )
}

export function KV({ k, v, mono = true }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 text-sm border-b border-line last:border-0">
      <span className="text-ink3">{k}</span>
      <span className={`${mono ? 'num' : ''} text-ink text-right`}>{v}</span>
    </div>
  )
}
