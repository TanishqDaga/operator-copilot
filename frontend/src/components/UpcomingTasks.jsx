import { CalendarClock, MapPin } from 'lucide-react'
import { SensitivityChips } from './WeatherImpactBadge'

/** UP NEXT — the next 2–3 assigned tasks in published order (read-only). */
export default function UpcomingTasks({ tasks }) {
  return (
    <div className="rounded-xl border border-line bg-panel2 p-4">
      <div className="label flex items-center gap-1.5"><CalendarClock size={12} /> Up next · published order</div>
      {tasks.length ? (
        <ol className="mt-3 space-y-3">
          {tasks.map((t) => (
            <li key={t.task_id} className="border-l-2 border-line2 pl-3">
              <div className="flex items-baseline justify-between gap-2">
                <span className="num text-sm font-semibold text-ink">{t.start}</span>
                <span className="num text-2xs text-ink3">{Math.round(t.planned_min)} min planned</span>
              </div>
              <div className="text-sm text-ink"><span className="num mr-1.5 text-2xs text-ink3">{t.task_id}</span>{t.name}</div>
              <div className="mt-0.5 flex flex-wrap items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1 text-2xs text-ink3"><MapPin size={11} /> {t.location}</span>
                <SensitivityChips profile={t.weather_sensitivity} />
              </div>
              {t.preparation[0] && <p className="mt-1 text-2xs text-ink3">Preparation: {t.preparation[0]}</p>}
            </li>
          ))}
        </ol>
      ) : <p className="mt-2 text-sm text-ink3">No further assigned tasks.</p>}
    </div>
  )
}
