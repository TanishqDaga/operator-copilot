import { CheckCircle2, CircleDashed, Clock, ListChecks, MapPin, Timer, TrendingDown, TrendingUp } from 'lucide-react'
import { fmt, signed } from '../lib/format'
import { useApp } from '../lib/store'
import { Card, CardHeader, Live, Progress } from './ui'

export function EtaCard() {
  const { state } = useApp()
  const t = state?.task
  const e = state?.eta
  if (!t || !e) {
    return (
      <Card className="p-6">
        <div className="label">Active task</div>
        <p className="mt-2 text-ink2">All planned tasks complete.</p>
      </Card>
    )
  }
  const up = e.changed_by > 0
  return (
    <Card className="overflow-hidden">
      <CardHeader icon={Timer} title={`${t.id} · ${t.name}`} subtitle={<span className="inline-flex items-center gap-1"><MapPin size={12} />{t.location} · {t.label} · {t.terrain} ground</span>} />
      <div className="grid gap-6 px-5 pb-5 md:grid-cols-[1.1fr_1fr]">
        <div>
          <div className="label">Remaining · predicted</div>
          <div className="mt-1 flex items-baseline gap-2">
            <Live value={e.minutes} className="text-6xl font-bold text-ink leading-none" />
            <span className="text-lg text-ink3">min</span>
            <span className="num rounded-lg border border-line2 bg-raised px-2 py-1 text-sm text-ink2">± {e.err_min} min</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink3">
            <span className="inline-flex items-center gap-1.5"><Clock size={14} /> Finish <span className="num text-ink">{e.finish}</span></span>
            <span>Recent cycle <span className="num text-ink">{fmt(e.recent_cycle_s)} s</span></span>
          </div>
        </div>
        <div className="flex flex-col justify-between gap-4">
          <div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-ink3">Material moved</span>
              <span className="num text-ink"><Live value={fmt(t.moved_t, 0)} /> / {t.tonnes} t</span>
            </div>
            <Progress value={t.progress} className="mt-2 h-2.5" />
            <div className="mt-1.5 text-2xs text-ink3 num">{Math.round(t.progress * 100)}% · {state.cycles} cycles this shift</div>
          </div>
          {e.changed_by !== 0 && e.reason ? (
            <div key={e.changed_at} className={`animate-rise rounded-xl border px-3 py-2.5 ${up ? 'border-warn/40 bg-warn-bg' : 'border-safe/40 bg-safe-bg'}`}>
              <div className={`flex items-center gap-2 text-sm font-bold ${up ? 'text-warn' : 'text-safe'}`}>
                {up ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                ETA changed by <span className="num">{signed(e.changed_by)} min</span>
                {e.changed_at && <span className="num ml-auto text-2xs font-medium text-ink3">{e.changed_at}</span>}
              </div>
              <p className="mt-1 text-[13px] text-ink2">because {e.reason.charAt(0).toLowerCase() + e.reason.slice(1)}</p>
            </div>
          ) : e.reason ? (
            <div key={e.changed_at} className="animate-rise rounded-xl border border-line2 bg-panel2 px-3 py-2.5">
              <div className="flex items-center gap-2 text-sm font-bold text-ink2">
                ETA re-predicted · no change (&lt; 1 min)
                {e.changed_at && <span className="num ml-auto text-2xs font-medium text-ink3">{e.changed_at}</span>}
              </div>
              <p className="mt-1 text-[13px] text-ink3">{e.reason}</p>
            </div>
          ) : (
            <div className="rounded-xl border border-line bg-panel2 px-3 py-2.5 text-[13px] text-ink3">No ETA change since the task started.</div>
          )}
        </div>
      </div>
    </Card>
  )
}

export function TaskList() {
  const { tasks } = useApp()
  const list = tasks?.tasks || []
  return (
    <Card>
      <CardHeader icon={ListChecks} title="Shift plan" subtitle={tasks?.plan} />
      <ul className="px-3 pb-3">
        {list.map((t) => (
          <li key={t.id} className={`flex items-center gap-3 rounded-xl px-3 py-3 ${t.status === 'active' ? 'bg-raised' : ''}`}>
            {t.status === 'done' ? <CheckCircle2 size={20} className="shrink-0 text-safe" /> : t.status === 'active'
              ? <span className="grid h-5 w-5 shrink-0 place-items-center"><span className="h-3 w-3 rounded-full bg-cat animate-pulse" /></span>
              : <CircleDashed size={20} className="shrink-0 text-ink3" />}
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <span className="num text-2xs text-ink3">{t.id}</span>
                <span className={`truncate text-sm font-medium ${t.status === 'done' ? 'text-ink3 line-through decoration-ink3/40' : 'text-ink'}`}>{t.name}</span>
              </div>
              <div className="mt-0.5 text-2xs text-ink3 truncate">{t.label} · {t.tonnes} t · {t.terrain}</div>
            </div>
            <div className="text-right">
              {t.status === 'done' ? (
                <>
                  <div className="num text-sm text-safe">{fmt(t.actual_min, 0)} min</div>
                  <div className="num text-2xs text-ink3">pred {fmt(t.predicted_at_start, 0)} ± {t.err_min}</div>
                </>
              ) : (
                <>
                  <div className="num text-sm text-ink">{t.eta_min} <span className="text-ink3">± {t.err_min}</span> min</div>
                  <div className="num text-2xs text-ink3">{t.status === 'active' ? 'finish' : 'est. done'} {t.finish}</div>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
    </Card>
  )
}
