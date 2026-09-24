import { Activity, CheckCircle2, ClipboardCheck, FileText, GraduationCap, NotebookPen, Power, Printer, ShieldAlert, Timer } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OperatorProductivitySummary } from '../components/ProductivityMetrics'
import { Card, CardHeader, Chip, KV, LevelPill, PageHeader, SyntheticTag } from '../components/ui'
import { api } from '../lib/api'
import { ANOMALY_LABEL, REASON_LABEL, fmt } from '../lib/format'
import { useApp } from '../lib/store'
import Gate from './Gate'

export default function Summary() {
  const { state, events, refreshAll } = useApp()
  const [s, setS] = useState(null)
  const [notes, setNotes] = useState('')
  const [saved, setSaved] = useState(false)
  const [confirmEnd, setConfirmEnd] = useState(false)
  const nav = useNavigate()

  useEffect(() => {
    let alive = true
    const load = () => api.get('/summary').then((r) => { if (alive) { setS(r); setNotes((n) => n || r.notes || '') } }).catch(() => {})
    load()
    const t = setInterval(load, 3000)
    return () => { alive = false; clearInterval(t) }
  }, [events.length])

  const saveNotes = async () => { await api.post('/shift/note', { text: notes }); setSaved(true); setTimeout(() => setSaved(false), 1500) }
  const end = async () => { await saveNotes(); await api.post('/shift/end'); await refreshAll(); setConfirmEnd(false); setS(await api.get('/summary')) }

  return (
    <Gate allowEnded what="the shift summary">
      {s?.available && (
        <div className="space-y-5">
          <PageHeader
            title="Shift summary & handoff"
            subtitle={`${s.operator.name} (${s.operator.id}) · ${s.machine_id} · ${s.start} – ${s.end} · ${fmt(s.duration_min, 0)} min`}
            right={
              <div className="no-print flex flex-wrap items-center gap-2">
                <SyntheticTag />
                <button className="btn btn-ghost btn-md" onClick={() => window.print()}><Printer size={16} /> Print / PDF</button>
                {state?.shift?.active ? (
                  confirmEnd ? (
                    <>
                      <button className="btn btn-danger btn-md" onClick={end}><Power size={16} /> Confirm end shift</button>
                      <button className="btn btn-quiet btn-md" onClick={() => setConfirmEnd(false)}>Cancel</button>
                    </>
                  ) : <button className="btn btn-primary btn-md" onClick={() => setConfirmEnd(true)}><Power size={16} /> End shift</button>
                ) : (
                  <button className="btn btn-primary btn-md" onClick={() => nav('/start')}>Start new shift</button>
                )}
              </div>
            }
          />
          <div className="flex items-center gap-2 text-sm">
            {s.ended ? <Chip tone="safe"><CheckCircle2 size={14} /> Shift closed — report final</Chip> : <Chip tone="cat">Shift in progress — live report</Chip>}
            <span className="text-ink3">Pre-start checklist completed {s.checklist.completed_at} ({s.checklist.items.length} items)</span>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 min-[1800px]:grid-cols-8">
            <Kpi label="Material moved" value={fmt(s.production.tonnes, 0)} unit="t" />
            <Kpi label="Cycles" value={s.production.cycles} sub={s.production.avg_cycle_s ? `avg ${s.production.avg_cycle_s} s` : 'no cycles yet'} />
            <Kpi label="Tasks done" value={`${s.production.tasks_done}/${s.production.tasks_total}`} />
            <Kpi label="Critical" value={s.safety.critical} tone={s.safety.critical ? 'text-crit' : 'text-ink'} />
            <Kpi label="Warning" value={s.safety.warning} tone={s.safety.warning ? 'text-warn' : 'text-ink'} />
            <Kpi label="Closest person" value={s.safety.closest_m != null ? fmt(s.safety.closest_m) : '—'} unit={s.safety.closest_m != null ? 'm' : ''} />
            <Kpi label="Idle total" value={fmt(s.idle.total_min)} unit="min" sub={`≈ ${fmt(s.idle.fuel_l)} L idle fuel`} />
            <Kpi label="Fuel used" value={fmt(s.fuel.used_l)} unit="L" sub={`${s.fuel.start_pct}% → ${s.fuel.now_pct}%`} />
          </div>

          <OperatorProductivitySummary s={s.operator_productivity} />

          <div className="grid gap-5 xl:grid-cols-2">
            <Card>
              <CardHeader icon={ShieldAlert} title="Safety events" subtitle={`${s.safety.events.length} rule-engine alerts · seatbelt ${s.safety.seatbelt} · wet ground ${s.safety.wet_ground}`} />
              <Table empty="No safety alerts this shift." rows={s.safety.events} cols={[
                ['Time', (e) => <span className="num">{e.ts}</span>],
                ['Level', (e) => <LevelPill level={e.level} size="sm" pulse={false} />],
                ['Reasons', (e) => e.reasons.map((r) => REASON_LABEL[r] || r).join(', ')],
                ['Distance', (e) => (e.distance_m != null ? <span className="num">{fmt(e.distance_m)} m</span> : '—')],
                ['Source', (e) => (e.distance_m != null ? e.source : 'machine')],
              ]} />
            </Card>
            <Card>
              <CardHeader icon={Timer} title="Tasks" subtitle="Predicted at task start vs actual" />
              <Table rows={s.production.tasks} cols={[
                ['Task', (t) => <span><span className="num text-ink3">{t.id}</span> {t.name}</span>],
                ['Status', (t) => <Chip tone={t.status === 'done' ? 'safe' : t.status === 'active' ? 'cat' : 'default'}>{t.status}</Chip>],
                ['Moved', (t) => <span className="num whitespace-nowrap">{fmt(t.moved_t, 0)}/{t.tonnes} t</span>],
                ['Predicted', (t) => (t.predicted_at_start != null ? <span className="num whitespace-nowrap">{fmt(t.predicted_at_start, 0)} ± {t.err_min}</span> : <span className="num whitespace-nowrap text-ink3">{t.eta_min} ± {t.err_min}</span>)],
                ['Actual', (t) => (t.actual_min != null ? <span className="num">{fmt(t.actual_min, 0)} min</span> : '—')],
              ]} />
            </Card>
            <Card>
              <CardHeader icon={Activity} title="Anomalies & ETA changes" subtitle="What slowed the shift down" />
              <div className="space-y-4 px-5 pb-5">
                {s.anomalies.length ? s.anomalies.map((a, i) => (
                  <div key={i} className="flex items-center justify-between rounded-xl border border-anom/30 bg-anom-bg px-4 py-3">
                    <div>
                      <div className="text-sm font-semibold text-anom">{ANOMALY_LABEL[a.type] || a.type}</div>
                      <div className="num text-2xs text-ink3">{a.started}{a.ended ? ` – ${a.ended}` : ' – ongoing'}</div>
                    </div>
                    <div className="num text-right text-sm text-ink">peak {fmt(a.peak)} {a.unit}<div className="text-2xs text-ink3">usual {fmt(a.baseline)} {a.unit}</div></div>
                  </div>
                )) : <p className="text-sm text-ink3">No anomalies flagged.</p>}
                <div>
                  <div className="label mb-2">ETA changes</div>
                  {s.eta_changes.length ? (
                    <ul className="space-y-1.5">
                      {s.eta_changes.map((e) => (
                        <li key={e.id} className="flex gap-3 text-sm">
                          <span className="num w-16 shrink-0 text-ink3">{e.ts}</span>
                          <span className={`num w-16 shrink-0 font-semibold ${e.changed_by > 0 ? 'text-warn' : 'text-safe'}`}>{e.changed_by > 0 ? '+' : ''}{e.changed_by} min</span>
                          <span className="text-ink2">{e.detail}</span>
                        </li>
                      ))}
                    </ul>
                  ) : <p className="text-sm text-ink3">No ETA changes.</p>}
                </div>
              </div>
            </Card>
            <Card>
              <CardHeader icon={GraduationCap} title="Training follow-up" subtitle="From today's events" />
              <div className="space-y-2 px-5 pb-5">
                {s.training.recommendations.length ? s.training.recommendations.map((r) => {
                  const b = s.training.bookings.find((x) => x.module_id === r.module.id)
                  return (
                    <div key={r.module.id} className="flex items-center justify-between gap-3 rounded-xl border border-line bg-panel2 px-4 py-3">
                      <div>
                        <div className="text-sm font-semibold text-ink">{r.module.title}</div>
                        <div className="text-2xs text-ink3">{r.reason}</div>
                      </div>
                      {b ? <Chip tone="safe"><span className="num">{b.slot}</span></Chip> : <Chip>Not booked</Chip>}
                    </div>
                  )
                }) : <p className="text-sm text-ink3">No training triggered this shift.</p>}
                <KV k="Weather during shift" v={s.weather.join(', ')} mono={false} />
                <KV k="Events logged" v={s.event_count} />
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader icon={NotebookPen} title="Handoff notes" subtitle="For the next operator and the supervisor"
              right={saved ? <span className="text-xs text-safe">Saved</span> : null} />
            <div className="px-5 pb-5">
              <textarea value={notes} onChange={(e) => setNotes(e.target.value)} onBlur={saveNotes} rows={4} disabled={s.ended}
                placeholder="Ground conditions, machine issues, anything the next shift should know…"
                className="w-full resize-y rounded-xl border border-line2 bg-panel2 p-4 text-sm text-ink placeholder:text-ink3 focus:border-cat/60 focus:outline-none" />
              <div className="mt-2 flex items-center gap-2 text-2xs text-ink3"><ClipboardCheck size={12} /> Saved with the shift report when you leave the field or end the shift.</div>
            </div>
          </Card>
          <p className="flex items-center gap-2 text-2xs text-ink3"><FileText size={12} /> Generated by Operator Copilot from the event log, the rule engine and the models — synthetic data.</p>
        </div>
      )}
    </Gate>
  )
}

function Kpi({ label, value, unit, sub, tone = 'text-ink' }) {
  return (
    <div className="card px-4 py-3">
      <div className="label truncate">{label}</div>
      <div className={`num mt-1 text-2xl font-semibold ${tone}`}>{value} {unit && <span className="text-xs text-ink3">{unit}</span>}</div>
      {sub && <div className="num mt-0.5 text-2xs text-ink3 truncate">{sub}</div>}
    </div>
  )
}

function Table({ rows, cols, empty }) {
  if (!rows.length) return <p className="px-5 pb-5 text-sm text-ink3">{empty}</p>
  return (
    <div className="overflow-x-auto px-5 pb-5">
      <table className="w-full text-sm">
        <thead><tr>{cols.map(([h]) => <th key={h} className="label py-2 pr-3 text-left font-semibold">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i} className="border-t border-line">
              {cols.map(([h, f]) => <td key={h} className="py-2.5 pr-3 text-ink2">{f(r)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
