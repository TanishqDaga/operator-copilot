import { toMin } from '../lib/format'

const BAR = {
  info: 'border-info/60 bg-info/20 text-info',
  safe: 'border-safe/50 bg-safe/15 text-safe',
  cat: 'border-cat/60 bg-cat/15 text-cat',
  locked: 'border-line2 bg-raised text-ink3',
  default: 'border-line2 bg-raised text-ink',
}

function tone(e) {
  const r = e.recommendation
  if (e.locked) return 'locked'
  if (!r) return 'default'
  if (r.source === 'manager_override') return 'cat'
  if (r.label?.endsWith('sensitive')) return 'info'
  if (r.label?.endsWith('tolerant')) return 'safe'
  return 'default'
}

/**
 * Gantt strip across the shift with forecast rain shading behind it.
 * rows: [{ label, entries }] — each entry needs task_id, name, start, end, start_min, end_min.
 */
export default function ScheduleTimeline({ rows, forecast, shift, highlight }) {
  if (!forecast || !shift) return null
  const s0 = toMin(shift.start)
  const s1 = toMin(shift.end)
  const span = s1 - s0
  const pct = (m) => `${((m - s0) / span) * 100}%`
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[720px]">
        <div className="relative ml-28 h-6">
          {forecast.hours.map((h) => (
            <span key={h.time} className="num absolute -translate-x-1/2 text-2xs text-ink3" style={{ left: pct(h.start_min) }}>{h.time}</span>
          ))}
          <span className="num absolute -translate-x-full text-2xs text-ink3" style={{ left: '100%' }}>{shift.end}</span>
        </div>
        {rows.map((row) => (
          <div key={row.label} className="flex items-stretch gap-2 py-1">
            <div className="flex w-[104px] shrink-0 items-center text-2xs font-semibold uppercase tracking-wider text-ink3">{row.label}</div>
            <div className="relative h-12 flex-1 overflow-hidden rounded-lg border border-line bg-panel2">
              {forecast.hours.map((h) => (
                <div key={h.time} className="absolute inset-y-0 border-l border-line/60 bg-info"
                  style={{ left: pct(h.start_min), width: `${(60 / span) * 100}%`, opacity: (h.rain_probability / 100) * 0.28 }}
                  title={`${h.time} · ${h.rain_probability}% rain`} />
              ))}
              {row.entries.map((e) => (
                <div key={e.task_id} title={`${e.task_id} ${e.name} · ${e.start}–${e.end}${e.recommendation ? ` · ${e.recommendation.label}` : ''}`}
                  className={`absolute inset-y-1.5 flex items-center gap-1.5 overflow-hidden rounded-md border px-2 text-2xs font-semibold ${BAR[tone(e)]} ${highlight === e.task_id ? 'ring-2 ring-cat' : ''}`}
                  style={{ left: `calc(${pct(e.start_min)} + 1px)`, width: `calc(${((e.end_min - e.start_min) / span) * 100}% - 2px)` }}>
                  <span className="num shrink-0">{e.task_id}</span>
                  <span className="truncate font-medium text-ink2">{e.name}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div className="ml-28 mt-2 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-ink3">
          <Legend cls={BAR.info} label="Moved for its own weather sensitivity" />
          <Legend cls={BAR.safe} label="Weather-tolerant, placed in poorer weather" />
          <Legend cls={BAR.cat} label="Manager override" />
          <Legend cls={BAR.locked} label="Started / completed (locked)" />
          <span className="inline-flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm bg-info/30" /> Shading = forecast rain probability</span>
        </div>
      </div>
    </div>
  )
}

function Legend({ cls, label }) {
  return <span className="inline-flex items-center gap-1.5"><span className={`h-3 w-3 rounded-sm border ${cls}`} /> {label}</span>
}
