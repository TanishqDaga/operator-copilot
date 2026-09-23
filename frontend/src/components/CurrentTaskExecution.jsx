import { ChevronRight, Clock, MapPin, Timer } from 'lucide-react'
import { useState } from 'react'
import { fmt } from '../lib/format'
import { SensitivityChips } from './WeatherImpactBadge'
import { Chip, KV, Progress } from './ui'

const SCHED = {
  early: (d) => ({ tone: 'safe', text: `Projected ${Math.round(d)} min early` }),
  late: (d) => ({ tone: 'warn', text: `About ${Math.round(-d)} min behind` }),
  on_schedule: () => ({ tone: 'default', text: 'On schedule' }),
}

/** Current assigned task: window, progress, live ETA and schedule status. Click for full task details. */
export default function CurrentTaskExecution({ task, state }) {
  const [open, setOpen] = useState(false)
  if (!task) {
    return (
      <div className="rounded-xl border border-line bg-panel2 p-4">
        <div className="label">Current task</div>
        <p className="mt-2 text-sm text-ink2">{state?.detail || 'No task in progress.'}</p>
      </div>
    )
  }
  const s = task.schedule_status ? SCHED[task.schedule_status](task.projected_delta_min) : null
  return (
    <div className="rounded-xl border border-cat/40 bg-panel2 p-4">
      <button className="group flex w-full items-start justify-between gap-3 text-left" onClick={() => setOpen((x) => !x)} aria-expanded={open}>
        <div className="min-w-0">
          <div className="label">Current task</div>
          <div className="mt-1 text-base font-semibold text-ink"><span className="num mr-2 text-2xs text-ink3">{task.task_id}</span>{task.name}</div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-2xs text-ink3">
            <span className="inline-flex items-center gap-1"><Clock size={11} /> <span className="num">{task.start}–{task.end}</span> published</span>
            <span className="inline-flex items-center gap-1"><MapPin size={11} /> {task.location}</span>
          </div>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 text-2xs font-semibold text-ink3 group-hover:text-cat">
          Task details <ChevronRight size={14} className={`transition-transform ${open ? 'rotate-90' : ''}`} />
        </span>
      </button>
      <div className="mt-3 flex items-baseline justify-between text-sm">
        <span className="text-ink3">Progress</span>
        <span className="num text-ink">{Math.round((task.progress || 0) * 100)}%</span>
      </div>
      <Progress value={task.progress || 0} className="mt-1.5" />
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-sm text-ink2">
          <Timer size={14} /> ETA <span className="num font-semibold text-ink">{task.eta_min != null ? `${Math.round(task.eta_min)} min` : '—'}</span>
          {task.eta_err_min != null && <span className="num text-2xs text-ink3">± {task.eta_err_min}</span>}
        </span>
        {s ? <Chip tone={s.tone} className="!py-0.5 !text-2xs">{s.text}</Chip>
          : <span className="text-2xs text-ink3">Early/late assessed once the ETA settles</span>}
      </div>
      {open && (
        <div className="mt-4 border-t border-line pt-3">
          <div className="label mb-1">Task details</div>
          <KV k="Task" v={task.name} mono={false} />
          <KV k="Location" v={task.location} mono={false} />
          <KV k="Scheduled (published)" v={`${task.start}–${task.end}`} />
          <KV k="ETA finish (live clock)" v={task.eta_finish ? `${task.eta_finish} (${fmt(task.eta_min, 0)} min)` : '—'} />
          <KV k="Weather sensitivity" v={<SensitivityChips profile={task.weather_sensitivity} />} mono={false} />
          <KV k="Current weather" v={task.current_weather} mono={false} />
          <KV k="Upcoming weather" v={task.upcoming_weather} mono={false} />
          <KV k="Progress" v={`${Math.round((task.progress || 0) * 100)}% of ${task.tonnes} t`} />
          <KV k="Operator guidance" v={task.guidance} mono={false} />
          <KV k="Next task" v={task.next ? `${task.next.task_id} ${task.next.name} (${task.next.start})` : 'Last assigned task'} mono={false} />
          {task.transition && (
            <KV k="Transition" mono={false} v={task.transition.relocation
              ? `Relocate ${task.transition.from} → ${task.transition.to}${task.transition.task_travel_m ? ` · ${task.transition.task_travel_m} m task travel` : ''}`
              : 'Same location'} />
          )}
          {task.manager_note && <p className="mt-2 text-2xs text-ink3">Manager's plan: {task.manager_note}</p>}
        </div>
      )}
    </div>
  )
}
