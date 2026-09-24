/**
 * Recommended Training tab — exact logic from the original Training.jsx,
 * plus navigation CTAs to Video Guide and AI Assistant, and deep-link buttons
 * on each recommendation card to the relevant video lessons.
 *
 * The underlying event → recommendation mapping in the backend is NOT changed.
 */
import {
  BookOpen,
  CalendarCheck,
  CalendarPlus,
  Check,
  Clock,
  GraduationCap,
  Loader2,
  MonitorPlay,
  Sparkles,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, Chip, Empty } from '../../components/ui'
import { getLessonsForModule } from '../../data/videoGuide'
import { api } from '../../lib/api'
import { useApp } from '../../lib/store'

export default function RecommendedTraining() {
  const { events } = useApp()
  const [data, setData] = useState(null)
  const [booking, setBooking] = useState(null)

  const load = useCallback(
    () => api.get('/training').then(setData).catch(() => {}),
    []
  )
  useEffect(() => { load() }, [load, events.length])

  const recIds = new Set(data?.recommendations?.map((r) => r.module.id))
  const others = data?.modules?.filter((m) => !recIds.has(m.id)) || []

  return (
    <div className="space-y-5">
      {!data ? null : (
        <>
          {/* ── Recommended Modules ───────────────────────────────────────── */}
          <Card>
            <CardHeader
              icon={Sparkles}
              title="Recommended from today's events"
              subtitle={`${data.recommendations.length} of ${data.modules.length} modules triggered`}
            />
            {data.recommendations.length ? (
              <div className="grid gap-4 px-5 pb-5 lg:grid-cols-2">
                {data.recommendations.map((r) => (
                  <ModuleCard
                    key={r.module.id}
                    m={r.module}
                    reason={r.reason}
                    count={r.count}
                    onBook={() => setBooking(r.module)}
                    booked={data.bookings.find((b) => b.module_id === r.module.id)}
                  />
                ))}
              </div>
            ) : (
              <Empty icon={GraduationCap} title="Nothing triggered yet">
                Proximity warnings, excess idle, seatbelt events and rain each map to a
                module. Recommendations appear as they happen.
              </Empty>
            )}
          </Card>

          {/* ── Other Modules + Bookings ──────────────────────────────────── */}
          <div className="grid gap-5 xl:grid-cols-[1.5fr_1fr]">
            <Card>
              <CardHeader
                icon={BookOpen}
                title="Other modules"
                subtitle="Not triggered by today's events"
              />
              <div className="grid gap-3 px-5 pb-5 md:grid-cols-2">
                {others.length
                  ? others.map((m) => (
                    <div key={m.id} className="rounded-xl border border-line bg-panel2 p-4">
                      <div className="font-semibold text-ink">{m.title}</div>
                      <p className="mt-1 text-[13px] text-ink3">{m.summary}</p>
                      <div className="mt-3 flex gap-2 text-2xs text-ink3">
                        <Clock size={12} /> {m.duration_min} min · {m.format}
                      </div>
                    </div>
                  ))
                  : <p className="text-sm text-ink3">Every module has been recommended today.</p>}
              </div>
            </Card>

            <Card>
              <CardHeader
                icon={CalendarCheck}
                title="Instructor bookings"
                subtitle="Saved to training.json"
              />
              <ul className="space-y-2 px-5 pb-5">
                {data.bookings.length
                  ? data.bookings.map((b) => (
                    <li key={b.id} className="rounded-xl border border-line bg-panel2 px-4 py-3 animate-rise">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-ink">{b.title}</span>
                        <span className="num text-2xs text-ink3">{b.operator_id}</span>
                      </div>
                      <div className="num mt-1 text-sm text-cat">{b.slot}</div>
                      <div className="mt-1 text-2xs text-ink3">{b.reason}</div>
                    </li>
                  ))
                  : <p className="text-sm text-ink3">No sessions booked yet.</p>}
              </ul>
            </Card>
          </div>
        </>
      )}

      {booking && (
        <BookModal
          m={booking}
          slots={data.slots}
          onClose={() => setBooking(null)}
          onDone={() => { setBooking(null); load() }}
        />
      )}
    </div>
  )
}

// ── Module Card ────────────────────────────────────────────────────────────────

function ModuleCard({ m, reason, count, onBook, booked }) {
  const navigate = useNavigate()
  const linkedLessons = getLessonsForModule(m.id)

  return (
    <div className="flex flex-col rounded-2xl border border-cat/25 bg-gradient-to-b from-cat/[0.05] to-transparent p-5 animate-rise">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-ink">{m.title}</div>
          <div className="mt-1 flex items-center gap-3 text-2xs text-ink3">
            <span className="inline-flex items-center gap-1"><Clock size={12} /> {m.duration_min} min</span>
            <span className="inline-flex items-center gap-1"><MonitorPlay size={12} /> {m.format}</span>
          </div>
        </div>
        <Chip tone="cat"><span className="num">{count}</span> event{count === 1 ? '' : 's'}</Chip>
      </div>

      <div className="mt-4 rounded-xl border border-line bg-panel2 px-3 py-2.5">
        <div className="label">Why you're seeing this</div>
        <div className="mt-1 text-sm font-medium text-ink">{reason}</div>
      </div>

      <p className="mt-3 flex-1 text-[13px] text-ink3">{m.summary}</p>

      {/* Deep-link to video guide lessons */}
      {linkedLessons.length > 0 && (
        <div className="mt-3 rounded-xl border border-info/20 bg-info/5 px-3 py-2.5">
          <div className="label text-info/70">Learn in Video Guide</div>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {linkedLessons.slice(0, 2).map((lesson) => (
              <button
                key={lesson.id}
                className="inline-flex items-center gap-1 rounded-lg border border-info/25 bg-info/10 px-2.5 py-1 text-xs font-medium text-info hover:bg-info/15 transition-colors"
                onClick={() => navigate('/training/video')}
              >
                {lesson.title} →
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4">
        {booked ? (
          <div className="inline-flex items-center gap-2 text-sm font-semibold text-safe">
            <Check size={16} /> Booked · <span className="num">{booked.slot}</span>
          </div>
        ) : (
          <button className="btn btn-primary btn-md" onClick={onBook}>
            <CalendarPlus size={16} /> Book instructor
          </button>
        )}
      </div>
    </div>
  )
}

// ── Book Modal ─────────────────────────────────────────────────────────────────

function BookModal({ m, slots, onClose, onDone }) {
  const [slot, setSlot] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const book = async () => {
    setBusy(true); setErr(null)
    try {
      await api.post('/training/book', { module_id: m.id, slot })
      onDone()
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md card p-6 animate-rise">
        <button
          className="absolute right-4 top-4 text-ink3 hover:text-ink"
          onClick={onClose}
          aria-label="Close"
        >
          <X size={18} />
        </button>
        <div className="label">Book instructor</div>
        <h3 className="mt-1 text-lg font-semibold text-ink">{m.title}</h3>
        <p className="mt-1 text-sm text-ink3">{m.duration_min} min · {m.format}</p>

        <div className="mt-5 grid grid-cols-2 gap-2">
          {slots.map((s) => (
            <button
              key={s.slot}
              disabled={s.taken}
              onClick={() => setSlot(s.slot)}
              className={`rounded-xl border px-3 py-3 text-left text-sm transition-colors disabled:opacity-40 ${
                slot === s.slot
                  ? 'border-cat bg-cat/10 text-ink'
                  : 'border-line bg-panel2 text-ink2 hover:border-line2'
              }`}
            >
              <div className="num font-semibold">{s.label}</div>
              <div className="text-2xs text-ink3">{s.taken ? 'Taken' : 'Available'}</div>
            </button>
          ))}
        </div>

        {err && <p className="mt-3 text-sm text-crit">{err}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button className="btn btn-ghost btn-md" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-md" disabled={!slot || busy} onClick={book}>
            {busy ? <Loader2 size={16} className="animate-spin" /> : <CalendarCheck size={16} />}
            Confirm booking
          </button>
        </div>
      </div>
    </div>
  )
}
