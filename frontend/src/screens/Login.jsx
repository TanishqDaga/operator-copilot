import { ArrowRight, Check, ClipboardList, HardHat, ShieldAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SyntheticTag } from '../components/ui'
import { HOME } from '../lib/session'
import { useApp } from '../lib/store'

const MANAGER = { id: 'MGR-01', name: 'J. Okafor' }

export default function Login() {
  const { meta, login, role } = useApp()
  const nav = useNavigate()
  const [pick, setPick] = useState('operator')
  const [op, setOp] = useState(null)

  useEffect(() => { if (meta && !op) setOp(meta.default_operator) }, [meta, op])
  useEffect(() => { if (role) nav(HOME[role], { replace: true }) }, [role, nav])

  const go = () => {
    if (pick === 'manager') login('manager', MANAGER.id, MANAGER.name)
    else {
      const o = meta?.operators?.find((x) => x.id === op)
      if (o) login('operator', o.id, o.name)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-bg px-4 py-10 grid-bg">
      <div className="w-full max-w-[560px]">
        <div className="mb-6 flex items-center gap-3">
          <svg viewBox="0 0 32 32" className="h-10 w-10 shrink-0">
            <path d="M16 2l12 7v14l-12 7-12-7V9z" fill="#FFCD11" />
            <path d="M16 9l6 3.5v7L16 23l-6-3.5v-7z" fill="#0A0C0F" />
          </svg>
          <div>
            <div className="text-lg font-extrabold tracking-tight text-ink">Operator Copilot</div>
            <div className="text-2xs font-semibold uppercase tracking-[0.16em] text-cat">Sign in · demo session</div>
          </div>
          <SyntheticTag className="ml-auto" />
        </div>

        <section className="card p-5">
          <div className="label mb-3">Choose a role</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <RoleCard active={pick === 'manager'} onClick={() => setPick('manager')} icon={ClipboardList} title="Manager"
              sub="Plan tasks, assign crews, review the weather-aware plan and publish the schedule" />
            <RoleCard active={pick === 'operator'} onClick={() => setPick('operator')} icon={HardHat} title="Operator"
              sub="Your published schedule, pre-start checklist and the live in-cab copilot" />
          </div>

          {pick === 'operator' && (
            <div className="mt-5">
              <div className="label mb-2">Operator</div>
              <div className="grid gap-2 sm:grid-cols-2">
                {meta?.operators?.map((o) => (
                  <button key={o.id} onClick={() => setOp(o.id)}
                    className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors ${op === o.id ? 'border-cat/60 bg-cat/[0.07]' : 'border-line hover:bg-raised'}`}>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-semibold text-ink">{o.name}</span>
                      <span className="num block text-2xs text-ink3">{o.id} · {o.experience_yrs} yrs</span>
                    </span>
                    {op === o.id && <Check size={16} className="text-cat" />}
                  </button>
                ))}
              </div>
            </div>
          )}
          {pick === 'manager' && (
            <p className="mt-5 rounded-xl border border-line bg-panel2 px-4 py-3 text-sm text-ink2">
              Signing in as <span className="font-semibold text-ink">{MANAGER.name}</span> <span className="num text-ink3">({MANAGER.id})</span>, site manager.
            </p>
          )}

          <button className="btn btn-primary btn-lg mt-5 w-full" onClick={go} disabled={pick === 'operator' && !op}>
            Continue as {pick === 'manager' ? 'Manager' : 'Operator'} <ArrowRight size={18} />
          </button>
        </section>

        <p className="mt-4 flex items-start gap-2 text-2xs leading-4 text-ink3">
          <ShieldAlert size={13} className="mt-px shrink-0" />
          Prototype role selection only — there are no passwords and this is not real authentication. The chosen role is stored in
          this browser and sent with each request so the backend can apply its demo role checks.
        </p>
      </div>
    </div>
  )
}

function RoleCard({ active, onClick, icon: Icon, title, sub }) {
  return (
    <button onClick={onClick}
      className={`flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-colors ${active ? 'border-cat/60 bg-cat/[0.07]' : 'border-line bg-panel2 hover:border-line2'}`}>
      <span className={`grid h-10 w-10 place-items-center rounded-lg ${active ? 'bg-cat text-cat-ink' : 'bg-raised text-ink2'}`}><Icon size={20} /></span>
      <span className="text-base font-semibold text-ink">{title}</span>
      <span className="text-2xs leading-4 text-ink3">{sub}</span>
    </button>
  )
}
