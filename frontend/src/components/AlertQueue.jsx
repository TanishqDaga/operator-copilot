import { CheckCircle2, OctagonAlert, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { LEVEL } from '../lib/format'
import { useApp } from '../lib/store'

const SOURCE_LEVEL = {
  safety: 'CRITICAL',
  productivity: 'ANOMALY',
  training: 'INFO',
}

export default function AlertQueue() {
  const { state } = useApp()
  const alerts = state?.alerts
  const headline = alerts?.headline
  const quiet = alerts?.quiet
  const n = alerts?.quiet_count || 0

  if (!headline) {
    return (
      <section className="relative overflow-hidden rounded-2xl border border-safe/30 bg-gradient-to-r from-safe-bg via-panel to-panel shadow-card">
        <div className="absolute inset-y-0 left-0 w-1.5 bg-safe" />
        <div className="flex items-center gap-5 p-6 md:p-7">
          <span className="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-safe/15 text-safe">
            <CheckCircle2 size={32} strokeWidth={2.2} />
          </span>
          <div className="min-w-0">
            <div className="label">Priority engine</div>
            <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-safe">All clear — continue the current task</h2>
          </div>
        </div>
      </section>
    )
  }

  const lvl = headline.id === 'prox' || headline.facts?.level === 'CRITICAL' ? 'CRITICAL'
    : headline.source === 'safety' ? 'WARNING'
      : SOURCE_LEVEL[headline.source] || 'INFO'
  const st = LEVEL[lvl] || LEVEL.INFO
  const Icon = headline.id === 'prox' ? OctagonAlert : ShieldAlert
  const crit = lvl === 'CRITICAL'

  return (
    <section className={`relative overflow-hidden rounded-2xl border ${st.border} shadow-card ${st.soft}`}>
      <div className={`absolute inset-y-0 left-0 w-1.5 ${st.bg} ${crit ? 'animate-critGlow' : ''}`} />
      <div className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:p-7">
        <span className={`grid h-16 w-16 shrink-0 place-items-center rounded-2xl ${st.bg} text-white ${crit ? 'animate-pulseRing' : ''}`}>
          <Icon size={32} strokeWidth={2.2} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="label">Do this now</div>
          <h2 className={`mt-1 text-2xl font-extrabold tracking-tight md:text-3xl ${st.text}`}>{headline.title}</h2>
          {n > 0 && quiet && (
            <p className="mt-3 text-sm text-ink2">
              <Link to="/timeline" className="font-semibold text-ink hover:text-cat">{quiet}</Link>
            </p>
          )}
        </div>
      </div>
    </section>
  )
}
