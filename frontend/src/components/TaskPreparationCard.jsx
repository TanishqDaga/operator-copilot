import { ArrowRight, ListTodo, MapPin } from 'lucide-react'
import { SensitivityChips } from './WeatherImpactBadge'

/** Next assigned task + what to prepare, derived from task data (location, type, travel, weather). */
export default function TaskPreparationCard({ task, live }) {
  if (!task) {
    return (
      <div className="rounded-xl border border-line bg-panel2 p-4">
        <div className="label">Next task</div>
        <p className="mt-2 text-sm text-ink2">No further assigned tasks in the published schedule.</p>
      </div>
    )
  }
  const gap = task.gap_after_current_min
  return (
    <div className="rounded-xl border border-line bg-panel2 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="label">Next task · prepare</div>
          <div className="mt-1 text-base font-semibold text-ink"><span className="num mr-2 text-2xs text-ink3">{task.task_id}</span>{task.name}</div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-3 text-2xs text-ink3">
            <span className="num">{task.start}–{task.end} published · {Math.round(task.planned_min)} min planned</span>
            <span className="inline-flex items-center gap-1"><MapPin size={11} /> {task.location}</span>
          </div>
        </div>
        {live && task.time_to_next_task_min != null && (
          <div className="shrink-0 text-right">
            <div className="label">Begins in</div>
            <div className="num text-xl font-semibold text-ink">~{Math.round(task.time_to_next_task_min)}<span className="text-xs text-ink3"> min</span></div>
          </div>
        )}
      </div>
      {live && gap != null && gap >= 3 && (
        <p className="mt-2 text-2xs text-safe">Current task is projected to finish ~{Math.round(gap)} min before this task's slot — time for post-task checks and preparation.</p>
      )}
      <ul className="mt-3 space-y-1.5">
        {task.preparation.map((p) => (
          <li key={p} className="flex items-start gap-2 text-[13px] text-ink2"><ListTodo size={14} className="mt-0.5 shrink-0 text-cat" /> {p}</li>
        ))}
      </ul>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <SensitivityChips profile={task.weather_sensitivity} />
        {task.transition?.relocation && (
          <span className="inline-flex items-center gap-1 text-2xs text-ink3">{task.transition.from} <ArrowRight size={11} /> {task.transition.to}</span>
        )}
      </div>
    </div>
  )
}
