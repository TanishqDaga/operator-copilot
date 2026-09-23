import { ListChecks, Lock, MapPin, Pencil, Plus, Trash2 } from 'lucide-react'
import { DURATION_SOURCE } from '../lib/format'
import AssignmentSelector from './AssignmentSelector'
import { MoveBadge, SensitivityChips } from './WeatherImpactBadge'
import { Card, CardHeader, Chip } from './ui'

const LIVE = { active: { tone: 'cat', label: 'In progress' }, done: { tone: 'safe', label: 'Done' } }

/**
 * All planner tasks with assignment, duration, original vs recommended position/window and the reason.
 * `schedule` is the recommended schedule when fresh, otherwise null (original preview is shown).
 */
export default function TaskPlanner({ tasks, original, schedule, operators, machines, busy, onAssign, onEdit, onDelete, onCreate }) {
  const oBy = Object.fromEntries((original || []).map((x) => [x.task_id, x]))
  const rBy = Object.fromEntries((schedule || []).map((x) => [x.task_id, x]))
  return (
    <Card>
      <CardHeader icon={ListChecks} title="Task planner" subtitle={`${tasks.length} tasks · original order is the manager's sequence`}
        right={<button className="btn btn-primary btn-sm" onClick={onCreate} disabled={busy}><Plus size={15} /> New task</button>} />
      <div className="overflow-x-auto px-5">
        <table className="w-full min-w-[1080px] text-left text-sm">
          <thead>
            <tr className="border-b border-line text-2xs uppercase tracking-wider text-ink3">
              <th className="py-2 pr-3 font-semibold">Task</th>
              <th className="py-2 pr-3 font-semibold">Assignment</th>
              <th className="py-2 pr-3 font-semibold">Duration</th>
              <th className="py-2 pr-3 font-semibold">Position</th>
              <th className="py-2 pr-3 font-semibold">Scheduled</th>
              <th className="py-2 pr-3 font-semibold">Weather sensitivity</th>
              <th className="py-2 pr-3 font-semibold">Recommendation</th>
              <th className="py-2 font-semibold"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => {
              const o = oBy[t.id]
              const r = rBy[t.id]
              const live = LIVE[t.live_status]
              const locked = !!live
              return (
                <tr key={t.id} className="border-b border-line align-top last:border-0">
                  <td className="py-3 pr-3">
                    <div className="flex items-baseline gap-2">
                      <span className="num text-2xs text-ink3">{t.id}</span>
                      <span className="font-medium text-ink">{t.name}</span>
                    </div>
                    <div className="mt-0.5 flex items-center gap-1 text-2xs text-ink3"><MapPin size={11} /> {t.location}</div>
                    <div className="mt-1 flex flex-wrap gap-1.5 text-2xs text-ink3">
                      <span>{t.label}</span>·<span className="num">{t.tonnes} t</span>·<span className="num">{t.distance_m} m</span>·<span>{t.terrain}</span>
                      <span className="num">· P{t.priority}</span>
                    </div>
                    {live && <Chip tone={live.tone} className="mt-1.5 !py-0.5 !text-2xs"><Lock size={11} /> {live.label}</Chip>}
                  </td>
                  <td className="py-3 pr-3">
                    <AssignmentSelector operator={t.assigned_operator} machine={t.assigned_machine} operators={operators} machines={machines}
                      disabled={busy || locked} onChange={(op, mc) => onAssign(t.id, op, mc)} />
                  </td>
                  <td className="py-3 pr-3">
                    <div className="num text-ink">{Math.round(t.planned_min)} min</div>
                    <div className="text-2xs text-ink3">{DURATION_SOURCE[t.duration_source]}</div>
                    <div className="num text-2xs text-ink3">ETA model {Math.round(t.eta_model_min)} min</div>
                  </td>
                  <td className="num py-3 pr-3 text-ink2">
                    #{o?.position ?? '—'} <span className="text-ink3">→</span> <span className={r && r.position !== o?.position ? 'font-semibold text-cat' : ''}>{r ? `#${r.position}` : '—'}</span>
                  </td>
                  <td className="num py-3 pr-3">
                    {r ? <span className="text-ink">{r.start}–{r.end}</span> : <span className="text-ink3">{o?.start}–{o?.end}</span>}
                    <div className="text-2xs text-ink3">{r ? `${r.effective_min} min wx-adjusted` : 'original order'}</div>
                  </td>
                  <td className="py-3 pr-3"><SensitivityChips profile={t.weather_sensitivity} /></td>
                  <td className="max-w-[300px] py-3 pr-3">
                    {r?.recommendation ? (
                      <>
                        <MoveBadge rec={r.recommendation} className="!text-2xs" />
                        <p className="mt-1 line-clamp-3 text-2xs leading-4 text-ink3" title={r.recommendation.reason}>{r.recommendation.reason}</p>
                      </>
                    ) : <span className="text-2xs text-ink3">Generate the plan to see a recommendation</span>}
                    {r?.warnings?.length > 0 && <p className="mt-1 text-2xs text-warn">{r.warnings.join(' · ')}</p>}
                  </td>
                  <td className="py-3">
                    <div className="flex gap-1">
                      <button className="btn btn-quiet h-9 w-9" title={locked ? 'Started tasks cannot be edited' : 'Edit'} disabled={busy || locked} onClick={() => onEdit(t)}><Pencil size={15} /></button>
                      <button className="btn btn-quiet h-9 w-9 hover:!text-crit" title={locked ? 'Started tasks cannot be deleted' : 'Delete'} disabled={busy || locked} onClick={() => onDelete(t)}><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
