import {
  Activity, CalendarRange, CheckCircle2, CloudRain, FlaskConical, GraduationCap, Info, Link2Off, MessageSquareText,
  OctagonAlert, Play, ShieldCheck, Timer, TriangleAlert,
} from 'lucide-react'
import { LEVEL, REASON_LABEL, fmt } from '../lib/format'
import { Chip } from './ui'

function iconFor(e) {
  if (e.kind === 'safety') return e.level === 'CRITICAL' ? OctagonAlert : e.level === 'WARNING' ? TriangleAlert : ShieldCheck
  return { anomaly: Activity, eta: Timer, weather: CloudRain, seatbelt: Link2Off, notice: Info, task: CheckCircle2,
    shift: Play, sim: FlaskConical, training: GraduationCap, planning: CalendarRange }[e.kind] || Info
}

export default function EventList({ events, compact = false }) {
  if (!events.length) return <p className="px-5 pb-5 text-sm text-ink3">No events yet this shift.</p>
  return (
    <ol className={`relative ${compact ? 'px-5 pb-4' : ''}`}>
      {events.map((e, i) => <EventRow key={e.id} e={e} compact={compact} last={i === events.length - 1} />)}
    </ol>
  )
}

function EventRow({ e, compact, last }) {
  const lv = LEVEL[e.level] || LEVEL.INFO
  const Icon = iconFor(e)
  return (
    <li className="relative flex gap-4 animate-rise">
      {!last && <span className="absolute left-[17px] top-10 bottom-0 w-px bg-line" />}
      <span className={`relative z-[1] mt-1 grid h-9 w-9 shrink-0 place-items-center rounded-xl border ${lv.border} ${lv.soft} ${lv.text}`}>
        <Icon size={16} />
      </span>
      <div className={`min-w-0 flex-1 ${compact ? 'pb-4' : 'pb-6'}`}>
        <div className="flex flex-wrap items-center gap-2">
          <span className="num text-xs text-ink3">{e.ts}</span>
          <span className={`text-2xs font-bold uppercase tracking-wider ${lv.text}`}>{e.kind === 'safety' ? e.level : e.kind}</span>
          {e.source && e.distance_m != null && <span className="text-2xs text-ink3">· via {e.source}</span>}
        </div>
        <div className={`mt-0.5 font-medium text-ink ${compact ? 'text-sm line-clamp-1' : 'text-[15px]'}`}>{e.title}</div>
        {!compact && (
          <>
            {e.detail && <p className="mt-1 text-sm text-ink3">{e.detail}</p>}
            {(e.reasons?.length > 0 || e.distance_m != null) && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {e.reasons?.map((r) => <Chip key={r} tone={e.level === 'CRITICAL' ? 'crit' : 'warn'}>{REASON_LABEL[r] || r}</Chip>)}
                {e.distance_m != null && <Chip><span className="num">{fmt(e.distance_m)} m</span></Chip>}
                {e.ttc_s != null && e.ttc_s < 60 && <Chip><span className="num">TTC {fmt(e.ttc_s)} s</span></Chip>}
                {e.speed_kmh > 0 && <Chip><span className="num">{fmt(e.speed_kmh)} km/h</span></Chip>}
              </div>
            )}
            {e.kind === 'planning' && (e.recommended_order || e.estimated_time_saved_min != null) && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {e.original_order && <Chip><span className="num">was {e.original_order.join(' → ')}</span></Chip>}
                {e.recommended_order && <Chip tone="info"><span className="num">{e.recommended_order.join(' → ')}</span></Chip>}
                {e.estimated_time_saved_min != null && <Chip tone="safe"><span className="num">est. {e.estimated_time_saved_min} min saved</span></Chip>}
              </div>
            )}
            {e.anomaly_type && e.current != null && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Chip tone="anom"><span className="num">now {fmt(e.current)} {e.unit}</span></Chip>
                <Chip tone="safe"><span className="num">usual {fmt(e.baseline)} {e.unit}</span></Chip>
              </div>
            )}
            {e.explanation && (
              <div className="mt-3 rounded-xl border border-line bg-panel2 px-3.5 py-2.5">
                <div className="flex items-start gap-2.5">
                  <MessageSquareText size={15} className="mt-0.5 shrink-0 text-ink3" />
                  <div className="min-w-0">
                    <p className="text-sm text-ink2">{e.explanation}</p>
                    <span className="text-2xs text-ink3">
                      {e.explanation_source === 'llm' ? 'LLM explanation' : 'Template explanation'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </li>
  )
}
