import { CalendarClock, CheckCircle2, CircleDashed, CloudRain, HelpCircle, MapPin, OctagonAlert, ThumbsUp, Truck } from 'lucide-react'
import { useState } from 'react'
import { useApp } from '../lib/store'
import WeatherImpactBadge, { SensitivityChips } from './WeatherImpactBadge'
import { Card, CardHeader, Chip, Empty, Source } from './ui'

const STATUS = {
  active: { tone: 'cat', label: 'Current' },
  done: { tone: 'safe', label: 'Done' },
  pending: { tone: 'default', label: 'Pending' },
  scheduled: { tone: 'default', label: 'Scheduled' },
}

/** Operator view of the published, weather-aware schedule. Read-only. */
export default function TodaySchedule() {
  const { schedule, acknowledgeSchedule } = useApp()
  const [ackErr, setAckErr] = useState(null)
  if (!schedule) return null
  if (!schedule.published) {
    return (
      <Card>
        <CardHeader icon={CalendarClock} title="Today's schedule" subtitle={`${schedule.operator.name} · ${schedule.shift.start}–${schedule.shift.end}`} />
        <Empty icon={CalendarClock} title="No schedule published yet">{schedule.message}</Empty>
      </Card>
    )
  }
  const cur = schedule.tasks.find((t) => t.task_id === schedule.current_id)
  const nxt = schedule.tasks.find((t) => t.task_id === schedule.next_id)
  const rest = schedule.tasks.filter((t) => t !== cur && t !== nxt)
  const prio = schedule.priority
  const ack = async () => {
    setAckErr(null)
    try { await acknowledgeSchedule() } catch (e) { setAckErr(e.message) }
  }
  return (
    <Card>
      <CardHeader icon={CalendarClock} title="Today's schedule"
        subtitle={`${schedule.schedule_id} · published by ${schedule.published_by} · forecast-based`}
        right={schedule.acknowledged_at
          ? <Chip tone="safe"><ThumbsUp size={13} /> Acknowledged</Chip>
          : <button className="btn btn-ghost btn-sm" onClick={ack}><ThumbsUp size={14} /> Acknowledge</button>} />

      {prio?.schedule_suppressed && (
        <div className="mx-5 mb-3 flex items-center gap-2.5 rounded-xl border border-crit/50 bg-crit-bg px-3.5 py-2.5 text-sm font-semibold text-crit">
          <OctagonAlert size={17} className="shrink-0" /> {prio.message}
          <span className="ml-auto text-2xs font-medium text-ink3">Priority {prio.top.priority} vs schedule 40</span>
        </div>
      )}
      <div className="mx-5 mb-3 flex items-start gap-2 rounded-xl border border-info/30 bg-info-bg px-3.5 py-2.5 text-[13px] text-info">
        <CloudRain size={16} className="mt-0.5 shrink-0" /> <span>{schedule.forecast.summary} <span className="text-ink3">(synthetic forecast)</span></span>
      </div>
      {schedule.modified_after_publish && <p className="mx-5 mb-3 text-2xs text-warn">{schedule.modified_after_publish}</p>}
      {ackErr && <p className="mx-5 mb-3 text-2xs text-crit">{ackErr}</p>}

      {schedule.tasks.length === 0 ? (
        <Empty icon={CalendarClock} title="Nothing assigned to you">{schedule.message}</Empty>
      ) : (
        <div className="space-y-4 px-5 pb-2">
          {cur && <Section label="Current task"><Item t={cur} suppressed={prio?.schedule_suppressed} emphasis /></Section>}
          {nxt && <Section label={cur ? 'Next task' : 'First task'}><Item t={nxt} suppressed={prio?.schedule_suppressed} emphasis={!cur} /></Section>}
          {rest.length > 0 && (
            <Section label="Remaining">
              <div className="space-y-2">{rest.map((t) => <Item key={t.task_id} t={t} suppressed={prio?.schedule_suppressed} />)}</div>
            </Section>
          )}
        </div>
      )}
      <Source className="px-5 py-4">
        Windows are planning estimates from the manager's published plan and a synthetic forecast — not guarantees. Live ETAs for the current
        task still come from the ETA model. Safety alerts always take priority over schedule recommendations.
      </Source>
    </Card>
  )
}

function Section({ label, children }) {
  return (
    <div>
      <div className="label mb-2">{label}</div>
      {children}
    </div>
  )
}

function Item({ t, emphasis, suppressed }) {
  const st = STATUS[t.status] || STATUS.scheduled
  const r = t.recommendation || {}
  const why = r.operator_note
  const Icon = t.status === 'done' ? CheckCircle2 : CircleDashed
  return (
    <div className={`rounded-xl border px-4 py-3 ${t.status === 'active' ? 'border-cat/50 bg-cat/[0.05]' : emphasis ? 'border-line2 bg-panel2' : 'border-line bg-panel'}`}>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
        <span className="num text-base font-semibold text-ink">{t.start}–{t.end}</span>
        <Chip tone={st.tone} className="!py-0.5 !text-2xs">
          {t.status === 'active' ? <span className="h-2 w-2 rounded-full bg-cat animate-pulse" /> : <Icon size={12} />} {st.label}
        </Chip>
        <SensitivityChips profile={t.weather_sensitivity} className="ml-auto" />
      </div>
      <div className={`mt-1 font-medium ${t.status === 'done' ? 'text-ink3 line-through decoration-ink3/40' : 'text-ink'}`}>
        <span className="num mr-2 text-2xs text-ink3">{t.task_id}</span>{t.name}
      </div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-2xs text-ink3">
        <span className="inline-flex items-center gap-1"><MapPin size={11} /> {t.location}</span>
        <span className="inline-flex items-center gap-1"><Truck size={11} /> {t.machine}</span>
        <span className="num">Forecast in window: ≤{t.weather.max_rain}% rain · ≤{t.weather.max_wind} km/h · ≥{t.weather.min_visibility} m</span>
      </div>
      {why && t.status !== 'done' && (
        <div className={`mt-2 flex items-start gap-2 rounded-lg border px-3 py-2 text-[13px] ${suppressed ? 'border-line bg-panel2 text-ink3' : 'border-info/30 bg-info-bg text-ink2'}`}>
          <HelpCircle size={14} className="mt-0.5 shrink-0 text-info" />
          <span>
            <span className="font-semibold text-info">{r.label?.endsWith('tolerant') ? 'Why during poor weather? ' : 'Why now? '}</span>
            {why}
            {r.confidence && <span className="text-ink3"> · {r.confidence} forecast confidence</span>}
            {suppressed && <span className="block text-2xs text-ink3">Advisory only — the active safety issue comes first.</span>}
          </span>
        </div>
      )}
      {r.weather_conflict && t.status !== 'done' && (
        <div className="mt-2"><WeatherImpactBadge impact={r.weather_impact} /> <span className="text-2xs text-warn">{r.weather_conflict}</span></div>
      )}
    </div>
  )
}
