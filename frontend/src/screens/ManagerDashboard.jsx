import {
  CalendarCheck, CalendarClock, Check, CloudSun, GitCompareArrows, HardHat, History, ListChecks, Loader2, OctagonAlert,
  RefreshCw, RotateCcw, Send, SlidersHorizontal, Sparkles, Timer, TriangleAlert, Truck, X,
} from 'lucide-react'
import { useCallback, useState } from 'react'
import ScheduleComparison from '../components/ScheduleComparison'
import ScheduleTimeline from '../components/ScheduleTimeline'
import TaskEditor from '../components/TaskEditor'
import TaskPlanner from '../components/TaskPlanner'
import WeatherForecast, { SyntheticForecastTag } from '../components/WeatherForecast'
import { Card, CardHeader, Chip, Empty, PageHeader, Stat } from '../components/ui'
import { PLAN_STATUS, plural } from '../lib/format'
import { useApp } from '../lib/store'

export default function ManagerDashboard() {
  const { planner, plannerError, plannerLoading, manager, state } = useApp()
  const [err, setErr] = useState(null)
  const [notice, setNotice] = useState(null)
  const [editor, setEditor] = useState({ open: false, task: null })
  const [overrideMode, setOverrideMode] = useState(false)

  const run = useCallback(async (fn, ok) => {
    setErr(null); setNotice(null)
    try {
      const v = await fn()
      if (ok) setNotice(ok)
      return v
    } catch (e) { setErr(e.message) }
  }, [])
  const closeEditor = useCallback(() => setEditor({ open: false, task: null }), [])

  if (!planner) {
    return (
      <Card>
        <Empty icon={plannerError ? TriangleAlert : Loader2} title={plannerError ? 'Planner unavailable' : 'Loading planner…'}>
          {plannerError || 'Fetching tasks, forecast and the current plan.'}
        </Empty>
      </Card>
    )
  }

  const rec = planner.recommendation
  const fresh = rec && !planner.stale
  const sm = rec?.summary
  const status = PLAN_STATUS[planner.plan_status] || PLAN_STATUS.draft
  const busy = plannerLoading
  const running = planner.live.running
  const prio = state?.planning?.priority
  const assignedOps = new Set(planner.tasks.map((t) => t.assigned_operator).filter(Boolean))
  const assignedMc = new Set(planner.tasks.map((t) => t.assigned_machine).filter(Boolean))

  const onDelete = (t) => {
    if (window.confirm(`Delete ${t.id} "${t.name}" from the plan?`)) run(() => manager.deleteTask(t.id), `${t.id} deleted`)
  }

  return (
    <div className="space-y-5">
      <PageHeader title={`${planner.shift.name} — Weather-aware planning`}
        subtitle={`${planner.plan_name} · ${planner.shift.date} · ${planner.shift.start}–${planner.shift.end}`}
        right={<div className="flex items-center gap-2"><Chip tone={status.tone}>{status.label}</Chip><SyntheticForecastTag /></div>} />

      {prio?.schedule_suppressed && running && (
        <div className="flex items-center gap-3 rounded-xl border border-crit/50 bg-crit-bg px-4 py-3 text-sm font-semibold text-crit">
          <OctagonAlert size={18} /> {prio.message}
          <span className="ml-auto text-2xs font-medium text-ink3">Live: {prio.top.title}</span>
        </div>
      )}
      {(err || plannerError) && (
        <div className="flex items-start gap-3 rounded-xl border border-crit/40 bg-crit-bg px-4 py-3 text-sm text-crit">
          <TriangleAlert size={17} className="mt-0.5 shrink-0" /> <span className="flex-1">{err || plannerError}</span>
          <button className="text-ink3 hover:text-ink" onClick={() => setErr(null)} aria-label="Dismiss"><X size={16} /></button>
        </div>
      )}
      {notice && !err && (
        <div className="flex items-center gap-3 rounded-xl border border-safe/40 bg-safe-bg px-4 py-2.5 text-sm text-safe">
          <Check size={16} /> {notice}
          <button className="ml-auto text-ink3 hover:text-ink" onClick={() => setNotice(null)} aria-label="Dismiss"><X size={16} /></button>
        </div>
      )}

      {/* A. Shift overview */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat icon={CalendarClock} label="Date" value={planner.shift.date.slice(5)} sub={planner.shift.date} />
        <Stat icon={Timer} label="Shift" value={`${planner.shift.start}–${planner.shift.end}`} sub={running ? `Live · ${planner.live.active || 'all done'} active` : 'Not started'} />
        <Stat icon={HardHat} label="Operators" value={assignedOps.size} sub={`of ${planner.operators.length} available`} />
        <Stat icon={Truck} label="Machines" value={assignedMc.size} sub={`of ${planner.machines.length} in fleet`} />
        <Stat icon={ListChecks} label="Tasks" value={planner.tasks.length} sub={planner.published ? `${planner.published.schedule_id} published` : 'none published'} />
        <Stat icon={CloudSun} label="Current weather" value={running ? state?.weather : '—'} sub={running ? 'in cab (simulated)' : 'shift not started'}
          tone={state?.weather === 'rain' && running ? 'warn' : undefined} />
      </div>

      {/* B. Weather forecast */}
      <WeatherForecast forecast={planner.forecast} scenarios={planner.scenarios} busy={busy}
        onScenario={(s) => run(() => manager.setScenario(s), 'Forecast scenario changed — generate the plan again to update the recommendation')} />

      {/* C–F. Tasks, create/edit, assignment */}
      <TaskPlanner tasks={planner.tasks} original={planner.original_schedule} schedule={fresh ? rec.recommended_schedule : null}
        operators={planner.operators} machines={planner.machines} busy={busy}
        onAssign={(id, op, mc) => run(() => manager.assign(id, op, mc))}
        onEdit={(t) => setEditor({ open: true, task: t })} onDelete={onDelete}
        onCreate={() => setEditor({ open: true, task: null })} />

      {/* Plan actions */}
      <Card>
        <CardHeader icon={Sparkles} title="Weather-aware plan"
          subtitle="Deterministic planner — the same tasks and forecast always give the same recommendation. No LLM decides the order." />
        <div className="flex flex-wrap items-center gap-2 px-5 pb-4">
          <button className="btn btn-primary btn-md" disabled={busy} onClick={() => run(manager.recommend, 'Weather-aware plan generated')}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />} Generate weather-aware plan
          </button>
          {running && (
            <button className="btn btn-ghost btn-md" disabled={busy} onClick={() => run(manager.replan, 'Future tasks recalculated — done and active tasks stay locked')}>
              <RefreshCw size={16} /> Replan future tasks
            </button>
          )}
          <button className="btn btn-ghost btn-md" disabled={busy || !fresh} onClick={() => { setOverrideMode(false); run(manager.accept, 'Recommendation accepted') }}>
            <Check size={16} /> Accept recommendation
          </button>
          <button className={`btn btn-md ${overrideMode ? 'btn-primary' : 'btn-ghost'}`} disabled={busy || !fresh} onClick={() => setOverrideMode((x) => !x)}>
            <SlidersHorizontal size={16} /> {overrideMode ? 'Done overriding' : 'Override'}
          </button>
          <button className="btn btn-ghost btn-md" disabled={busy || !fresh}
            onClick={() => run(manager.publish, running ? 'Schedule published — pending tasks re-sequenced in the live shift' : 'Daily schedule published to operators')}>
            <Send size={16} /> Publish schedule
          </button>
          <button className="btn btn-quiet btn-sm ml-auto" disabled={busy || running}
            title={running ? 'End the shift before resetting' : 'Restore tasks and forecast from tasks.json'}
            onClick={() => window.confirm('Reset the demo plan to the seed tasks and default forecast?') && run(manager.reset, 'Demo plan reset')}>
            <RotateCcw size={14} /> Reset demo plan
          </button>
        </div>
        {planner.stale && (
          <p className="mx-5 mb-4 flex items-center gap-2 rounded-lg border border-warn/40 bg-warn-bg px-3 py-2 text-sm text-warn">
            <TriangleAlert size={15} /> {planner.stale} — generate the plan again before publishing.
          </p>
        )}
        {!rec && (
          <p className="mx-5 mb-4 text-sm text-ink3">
            Preview below uses the original order. Generate the weather-aware plan to see what the forecast suggests.
          </p>
        )}
        {rec && sm && (
          <div className="border-t border-line px-5 py-4">
            <p className={`text-[15px] leading-6 ${fresh ? 'text-ink' : 'text-ink3'}`}>{sm.headline}</p>
            <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat label="Tasks reordered" value={sm.tasks_moved} sub={`of ${sm.tasks_total} by the planner`} />
              <Stat label="Estimated time saved" value={sm.estimated_time_saved_min} unit="min"
                tone={sm.estimated_time_saved_min > 0 ? 'safe' : sm.estimated_time_saved_min < 0 ? 'warn' : undefined} sub="estimated impact vs original" />
              <Stat label="Original total" value={Math.round(sm.original_total_min)} unit="min" sub={`finishes ${sm.original_finish}`} />
              <Stat label="Recommended total" value={Math.round(sm.recommended_total_min)} unit="min" sub={`finishes ${sm.recommended_finish}`} />
            </div>
            {(sm.conflicts?.length > 0 || sm.warnings?.length > 0) && (
              <ul className="mt-3 space-y-1">
                {sm.conflicts.map((c) => <li key={c.message} className="flex gap-1.5 text-2xs text-crit"><TriangleAlert size={12} className="mt-px shrink-0" /> {c.message}</li>)}
                {sm.warnings.map((w) => <li key={w} className="flex gap-1.5 text-2xs text-warn"><TriangleAlert size={12} className="mt-px shrink-0" /> {w}</li>)}
              </ul>
            )}
          </div>
        )}
      </Card>

      {/* Original vs recommended */}
      <Card>
        <CardHeader icon={GitCompareArrows} title="Original vs recommended schedule"
          subtitle={overrideMode ? 'Override mode — move tasks or pin a start time; the planner keeps your decision' : 'Timeline shaded by forecast rain probability'} />
        <div className="space-y-5 px-5 pb-5">
          <ScheduleTimeline forecast={planner.forecast} shift={planner.shift}
            rows={[{ label: 'Original', entries: planner.original_schedule },
              ...(rec ? [{ label: fresh ? 'Recommended' : 'Rec. (stale)', entries: rec.recommended_schedule }] : [])]} />
          {rec ? (
            <ScheduleComparison original={rec.original_schedule} recommended={rec.recommended_schedule} overrideMode={overrideMode && fresh} busy={busy}
              onOverride={(body) => run(() => manager.override(body), body.clear ? `${body.task_id} override cleared` : `Manager override saved for ${body.task_id}`)} />
          ) : (
            <p className="text-sm text-ink3">No recommendation yet.</p>
          )}
        </div>
      </Card>

      {/* Published */}
      <Card>
        <CardHeader icon={CalendarCheck} title="Published schedule"
          subtitle={planner.published ? `${planner.published.schedule_id} · ${planner.published.created_at.replace('T', ' ')} · by ${planner.published.manager_name}` : 'Nothing published yet — operators see an empty schedule'} />
        {planner.published && (
          <div className="space-y-2 px-5 pb-4 text-sm">
            <div className="num text-ink">{planner.published_order.join(' → ')}</div>
            <div className="text-2xs text-ink3">
              Forecast {planner.published.forecast_id} · {plural(Object.keys(planner.published.overrides).length, 'override')} ·
              acknowledged by {Object.keys(planner.published.acknowledged).join(', ') || 'no one yet'}
            </div>
            {planner.published.modified_after_publish && <p className="text-2xs text-warn">{planner.published.modified_after_publish}</p>}
            {running && <p className="text-2xs text-ink3">The live shift follows this order for future tasks only. It never reshuffles on its own — use Replan, then Publish.</p>}
          </div>
        )}
        {planner.history.length > 0 && (
          <div className="border-t border-line px-5 py-3">
            <div className="label mb-2 flex items-center gap-1.5"><History size={12} /> Earlier versions</div>
            <ul className="space-y-1 text-2xs text-ink3">
              {planner.history.slice(0, 5).map((h) => (
                <li key={h.schedule_id} className="num">{h.schedule_id} · {h.created_at.replace('T', ' ')} · {h.summary?.recommended_order?.join(' → ')} · {h.status}</li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      <TaskEditor open={editor.open} task={editor.task} tasks={planner.tasks} onClose={closeEditor}
        onSave={(payload) => (editor.task ? manager.updateTask(editor.task.id, payload) : manager.createTask(payload))} />
    </div>
  )
}
