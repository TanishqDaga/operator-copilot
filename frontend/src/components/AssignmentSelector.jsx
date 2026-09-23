import { HardHat, Truck } from 'lucide-react'

const SELECT = 'h-9 w-full rounded-lg border border-line2 bg-panel2 px-2 text-[13px] text-ink disabled:opacity-50 focus:border-cat/60 focus:outline-none'

/** Operator + machine pickers. Empty value = unassigned. */
export default function AssignmentSelector({ operator, machine, operators = [], machines = [], onChange, disabled }) {
  return (
    <div className="grid min-w-[180px] gap-1.5">
      <label className="relative">
        <HardHat size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-ink3" />
        <select className={`${SELECT} pl-7 ${!operator ? 'border-warn/50 text-warn' : ''}`} value={operator || ''} disabled={disabled}
          aria-label="Assigned operator" onChange={(e) => onChange(e.target.value || null, machine || null)}>
          <option value="">No operator</option>
          {operators.map((o) => <option key={o.id} value={o.id}>{o.id} · {o.name}</option>)}
        </select>
      </label>
      <label className="relative">
        <Truck size={13} className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-ink3" />
        <select className={`${SELECT} pl-7 ${!machine ? 'border-warn/50 text-warn' : ''}`} value={machine || ''} disabled={disabled}
          aria-label="Assigned machine" onChange={(e) => onChange(operator || null, e.target.value || null)}>
          <option value="">No machine</option>
          {machines.map((m) => <option key={m.id} value={m.id}>{m.id} · {m.model}</option>)}
        </select>
      </label>
    </div>
  )
}

export { SELECT }
