import { ChevronDown, HelpCircle, OctagonAlert, Target } from 'lucide-react'
import { useState } from 'react'
import { GUIDANCE_LABEL, GUIDANCE_TONE } from '../lib/format'
import { Chip } from './ui'

const WRAP = {
  crit: 'border-crit/70 bg-crit-bg', warn: 'border-warn/60 bg-warn-bg', anom: 'border-anom/50 bg-anom-bg',
  cat: 'border-cat/50 bg-cat/[0.07]', info: 'border-info/40 bg-info-bg', safe: 'border-safe/40 bg-safe-bg',
}
const TEXT = { crit: 'text-crit', warn: 'text-warn', anom: 'text-anom', cat: 'text-cat', info: 'text-info', safe: 'text-safe' }

/** The single recommended action, its reason, and everything it outranked. */
export default function NextBestAction({ nba, state, secondary = [] }) {
  const [open, setOpen] = useState(false)
  if (!nba) return null
  const tone = GUIDANCE_TONE[nba.category] || 'cat'
  const safety = nba.category.startsWith('SAFETY')
  const Icon = safety ? OctagonAlert : Target
  return (
    <div>
      <div key={nba.action} className={`animate-rise rounded-2xl border px-5 py-4 ${WRAP[tone]}`}>
        <div className="flex flex-wrap items-center gap-2">
          <Icon size={16} className={`${TEXT[tone]} ${nba.category === 'SAFETY_CRITICAL' ? 'animate-pulse' : ''}`} />
          <span className={`text-2xs font-bold uppercase tracking-[0.14em] ${TEXT[tone]}`}>Next best action</span>
          <Chip tone={tone} className="!py-0.5 !text-2xs">{GUIDANCE_LABEL[nba.category]}</Chip>
          {state && <Chip className="!py-0.5 !text-2xs">{state.label}</Chip>}
        </div>
        <p className={`mt-2 text-lg font-semibold leading-snug md:text-xl ${safety ? TEXT[tone] : 'text-ink'}`}>{nba.action}</p>
        <p className="mt-2 flex items-start gap-2 text-sm text-ink2">
          <HelpCircle size={15} className={`mt-0.5 shrink-0 ${TEXT[tone]}`} />
          <span><span className="font-semibold text-ink">Why? </span>{nba.reason}</span>
        </p>
      </div>
      {secondary.length > 0 && (
        <div className="mt-2">
          <button className="btn btn-quiet btn-sm -ml-2" onClick={() => setOpen((x) => !x)} aria-expanded={open}>
            <ChevronDown size={14} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            {safety ? `Deferred until the safety condition clears (${secondary.length})` : `Also worth knowing (${secondary.length})`}
          </button>
          {open && (
            <ul className="mt-1 space-y-1.5">
              {secondary.map((a) => (
                <li key={a.action} className={`rounded-xl border border-line bg-panel2 px-3.5 py-2.5 ${a.deferred ? 'opacity-70' : ''}`}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip tone={GUIDANCE_TONE[a.category]} className="!py-0 !text-2xs">{GUIDANCE_LABEL[a.category]}</Chip>
                    {a.deferred && <span className="text-2xs text-ink3">deferred — safety first</span>}
                  </div>
                  <p className="mt-1 text-sm text-ink">{a.action}</p>
                  <p className="text-2xs text-ink3">Why? {a.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
