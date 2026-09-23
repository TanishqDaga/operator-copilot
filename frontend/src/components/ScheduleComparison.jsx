import { ArrowRight, ChevronDown, ChevronUp, Lock, Pin, TriangleAlert, X } from 'lucide-react'
import { useState } from 'react'
import { DURATION_SOURCE } from '../lib/format'
import WeatherImpactBadge, { MoveBadge, SensitivityChips } from './WeatherImpactBadge'

/** Side-by-side ORIGINAL PLAN vs RECOMMENDED PLAN, then one explained row per task. */
export default function ScheduleComparison({ original, recommended, overrideMode, onOverride, busy }) {
  const oBy = Object.fromEntries(original.map((x) => [x.task_id, x]))
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-2">
        <PlanList title="Original plan" sub="Manager's order, forecast applied" entries={original} />
        <PlanList title="Recommended plan" sub="Forecast-based recommendation" entries={recommended} accent />
      </div>
      <ol className="space-y-2">
        {recommended.map((r) => (
          <Row key={r.task_id} r={r} o={oBy[r.task_id]} overrideMode={overrideMode} onOverride={onOverride} busy={busy}
            first={r.position === 1} last={r.position === recommended.length} />
        ))}
      </ol>
    </div>
  )
}

function PlanList({ title, sub, entries, accent }) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? 'border-cat/40 bg-cat/[0.04]' : 'border-line bg-panel2'}`}>
      <div className="flex items-baseline justify-between">
        <div className={`label ${accent ? '!text-cat' : ''}`}>{title}</div>
        <div className="text-2xs text-ink3">{sub}</div>
      </div>
      <ul className="mt-3 space-y-1.5">
        {entries.map((e) => (
          <li key={e.task_id} className="flex items-center gap-3 text-sm">
            <span className="num w-[92px] shrink-0 text-ink2">{e.start}–{e.end}</span>
            <span className="num w-7 shrink-0 font-semibold text-ink">{e.task_id}</span>
            <span className="truncate text-ink2">{e.name}</span>
            {e.delay_min >= 1 && <span className="num ml-auto shrink-0 text-2xs text-ink3">+{Math.round(e.delay_min)} min wx</span>}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Row({ r, o, overrideMode, onOverride, busy, first, last }) {
  const rec = r.recommendation || {}
  const [time, setTime] = useState(r.override?.start || r.start)
  const moved = rec.moved !== 'unchanged'
  const canEdit = overrideMode && !r.locked
  const pinned = !!r.override?.start
  return (
    <li className={`rounded-xl border px-4 py-3 ${rec.source === 'manager_override' ? 'border-cat/40 bg-cat/[0.04]' : moved ? 'border-line2 bg-panel2' : 'border-line bg-panel'}`}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="num text-sm font-bold text-ink">{r.task_id}</span>
          <span className="text-sm font-medium text-ink">{r.name}</span>
        </div>
        <div className="num flex items-center gap-2 text-xs text-ink2" title="Original position → recommended position">
          <span className="rounded-md border border-line2 px-1.5 py-0.5">#{o?.position} {o?.start}</span>
          <ArrowRight size={13} className={moved ? 'text-cat' : 'text-ink3'} />
          <span className={`rounded-md border px-1.5 py-0.5 ${moved ? 'border-cat/50 text-cat' : 'border-line2'}`}>#{r.position} {r.start}–{r.end}</span>
        </div>
        <MoveBadge rec={rec} />
        {!r.locked && <WeatherImpactBadge impact={rec.weather_impact} />}
        <SensitivityChips profile={r.weather_sensitivity} className="ml-auto" />
      </div>
      <p className="mt-2 text-[13px] leading-5 text-ink2">{rec.reason}</p>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-ink3">
        <span className="num">Planned {r.base_min} min ({DURATION_SOURCE[r.duration_source] || r.duration_source}) · weather-adjusted {r.effective_min} min</span>
        <span className="num">Window forecast: ≤{r.weather.max_rain}% rain · ≤{r.weather.max_wind} km/h · ≥{r.weather.min_visibility} m vis.</span>
        {rec.confidence && !r.locked && <span>Forecast confidence: {rec.confidence}</span>}
      </div>
      {(rec.weather_conflict || r.warnings?.length > 0) && (
        <div className="mt-2 space-y-1">
          {rec.weather_conflict && <Warn>{rec.weather_conflict}</Warn>}
          {r.warnings.map((w) => <Warn key={w}>{w}</Warn>)}
        </div>
      )}
      {overrideMode && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3">
          {r.locked ? (
            <span className="inline-flex items-center gap-1.5 text-2xs text-ink3"><Lock size={12} /> Already started — can't be re-ordered</span>
          ) : (
            <>
              <button className="btn btn-ghost btn-sm" disabled={!canEdit || busy || first || pinned} onClick={() => onOverride({ task_id: r.task_id, move: 'up' })}>
                <ChevronUp size={15} /> Earlier
              </button>
              <button className="btn btn-ghost btn-sm" disabled={!canEdit || busy || last || pinned} onClick={() => onOverride({ task_id: r.task_id, move: 'down' })}>
                <ChevronDown size={15} /> Later
              </button>
              <span className="mx-1 h-6 w-px bg-line" />
              <input type="time" step={300} value={time} onChange={(e) => setTime(e.target.value)} aria-label={`Pinned start for ${r.task_id}`}
                className="num h-9 rounded-lg border border-line2 bg-panel2 px-2 text-[13px] text-ink" />
              <button className="btn btn-ghost btn-sm" disabled={busy || !time} onClick={() => onOverride({ task_id: r.task_id, start: time })}>
                <Pin size={14} /> Pin start
              </button>
              {r.override && (
                <button className="btn btn-quiet btn-sm" disabled={busy} onClick={() => onOverride({ task_id: r.task_id, clear: true })}>
                  <X size={14} /> Clear override
                </button>
              )}
              {r.override?.recommended_start && (
                <span className="num ml-auto text-2xs text-ink3">Recommended {r.override.recommended_start} · Manager override {r.start}</span>
              )}
            </>
          )}
        </div>
      )}
    </li>
  )
}

function Warn({ children }) {
  return (
    <p className="flex items-start gap-1.5 text-2xs text-warn">
      <TriangleAlert size={12} className="mt-px shrink-0" /> {children}
    </p>
  )
}
