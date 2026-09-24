import { Camera, Cloud, CloudRain, Footprints, Gauge, Hourglass, ListOrdered, Play, SlidersHorizontal, Sun, Truck, UserX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useCamera } from '../lib/camera'
import { fmt } from '../lib/format'
import { useApp } from '../lib/store'
import { Segmented, Toggle } from './ui'

function useAction() {
  const { sim } = useApp()
  const [err, setErr] = useState(null)
  const run = async (a, v) => {
    setErr(null)
    try { await sim(a, v) } catch (e) { setErr(e.message) }
  }
  return [run, err]
}

export function PersonControls({ showCamera = true }) {
  const { state, meta } = useApp()
  const [run, err] = useAction()
  const src = state?.vision?.source || 'slider'
  const person = state?.person
  const [val, setVal] = useState(20)
  const dragging = useRef(false)
  const lastSent = useRef(0)

  useEffect(() => {
    if (!dragging.current && person?.detected && src === 'slider') setVal(Math.min(30, person.distance_m))
  }, [person?.distance_m, person?.detected, src])

  const send = (v, force) => {
    const now = Date.now()
    if (force || now - lastSent.current > 120) {
      lastSent.current = now
      run('move_worker', v)
    }
  }

  return (
    <div className="space-y-4">
      <Segmented
        value={src}
        onChange={(v) => run('person_source', v)}
        options={[
          { value: 'slider', label: 'Slider', icon: SlidersHorizontal },
          { value: 'camera', label: 'Camera', icon: Camera, disabled: !meta?.vision?.available },
        ]}
      />
      {src === 'slider' ? (
        <div>
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium text-ink2">Worker distance</span>
            <span className="num text-lg font-semibold text-ink">{person?.detected ? `${fmt(val)} m` : 'No person'}</span>
          </div>
          <input
            type="range" min={0.5} max={30} step={0.1} value={val} className="slider"
            aria-label="Worker distance in metres"
            onPointerDown={() => { dragging.current = true }}
            onPointerUp={(e) => { dragging.current = false; send(Number(e.currentTarget.value), true) }}
            onChange={(e) => { const v = Number(e.target.value); setVal(v); send(v) }}
          />
          <div className="grid grid-cols-2 gap-2">
            <button className="btn btn-ghost btn-md" title="Person walks from 20 m to 1.5 m at 1.4 m/s" onClick={() => run('walk_worker', { from: 20, to: 1.5, speed: 1.4 })}>
              <Footprints size={16} /> Walk-in
            </button>
            <button className="btn btn-ghost btn-md" onClick={() => run('move_worker', null)}>
              <UserX size={16} /> No person
            </button>
          </div>
          <p className="mt-2 text-2xs text-ink3">Walk-in: 20 m → 1.5 m at 1.4 m/s. Synthetic input. Drives the same rule engine path as the camera; approach speed is derived from how fast the distance changes.</p>
        </div>
      ) : (
        showCamera && <CameraView />
      )}
      {err && <p className="text-xs text-crit">{err}</p>}
    </div>
  )
}

export function CameraView() {
  const { stream, result, error } = useCamera()
  const { state } = useApp()
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current && stream) { ref.current.srcObject = stream; ref.current.play().catch(() => {}) }
  }, [stream])
  return (
    <div>
      <div className="relative aspect-video max-h-44 overflow-hidden rounded-xl border border-line2 bg-black">
        {stream ? <video ref={ref} muted playsInline className="h-full w-full object-cover" /> : (
          <div className="grid h-full place-items-center text-sm text-ink3">{error || 'Starting camera…'}</div>
        )}
        {result?.boxes?.map((b, i) => (
          <div key={i} className="absolute rounded border-2 border-cat" style={{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.w * 100}%`, height: `${b.h * 100}%` }}>
            <span className="absolute -top-5 left-0 rounded bg-cat px-1 text-2xs font-bold text-cat-ink">person {Math.round(b.conf * 100)}%</span>
          </div>
        ))}
        {state?.vision?.stale && stream && (
          <span className="absolute bottom-2 left-2 rounded bg-black/70 px-2 py-0.5 text-2xs text-warn">Feed stale — treated as no person</span>
        )}
      </div>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        <Mini label="Distance proxy" value={result?.distance_m != null ? `${fmt(result.distance_m)} m` : '—'} />
        <Mini label="Box height" value={result?.h_ratio != null ? `${Math.round(result.h_ratio * 100)}%` : '—'} />
        <Mini label="Approach" value={result?.detected ? `${fmt(result.approach_ms, 2)} m/s` : '—'} />
      </div>
    </div>
  )
}

function Mini({ label, value }) {
  return (
    <div className="rounded-lg border border-line bg-panel2 px-2 py-1.5">
      <div className="text-2xs text-ink3">{label}</div>
      <div className="num text-sm text-ink">{value}</div>
    </div>
  )
}

export function MachineControls({ only }) {
  const { state } = useApp()
  const [run, err] = useAction()
  const [mins, setMins] = useState(15)
  const show = (k) => !only || only.includes(k)
  return (
    <div className="space-y-4">
      {show('stack') && (
        <div>
          <button className="btn btn-primary btn-md w-full" onClick={() => run('stack_alerts')} title="Worker approaching + seatbelt + idle + task delay + training nudge">
            <ListOrdered size={16} /> Flagship: five signals at once
          </button>
          <p className="mt-2 text-2xs text-ink3">Fires five live signals. The cab shows only the worker-in-path headline; the other four are logged, not urgent.</p>
        </div>
      )}
      {show('idle') && (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-ink2">Idle stretch</span>
            {state?.idle && <span className="num text-sm text-anom">idle {fmt(state.idle_min)} min</span>}
          </div>
          <Segmented value={mins} onChange={setMins} options={[5, 10, 15, 20].map((m) => ({ value: m, label: `${m} min` }))} />
          <div className="mt-2 grid grid-cols-2 gap-2">
            <button className="btn btn-ghost btn-md" onClick={() => run('trigger_idle', mins)}>
              <Hourglass size={16} /> Trigger idle
            </button>
            <button className="btn btn-ghost btn-md" onClick={() => run('trigger_idle', 0)} disabled={!state?.idle}>
              <Play size={16} /> Resume work
            </button>
          </div>
          <p className="mt-2 text-2xs text-ink3">Fast-forwards the simulated clock by the chosen minutes with the machine idle.</p>
        </div>
      )}
      {show('seatbelt') && (
        <div className="space-y-2">
          <Toggle checked={!state?.seatbelt} onChange={(v) => run('seatbelt_off', v)} tone="crit" label="Seatbelt unfastened" sub="Rule alerts only when the machine moves" />
          <button className="btn btn-ghost btn-md w-full" onClick={() => run('tram')}>
            <Truck size={16} /> Tram / reposition machine
          </button>
        </div>
      )}
      {show('pace') && (
        <div>
          <div className="mb-2 flex items-center gap-1.5 text-sm font-medium text-ink2"><Gauge size={14} /> Operator pace (demo)</div>
          <Segmented
            value={state?.sim_pace || 'normal'}
            onChange={(v) => run('pace', v)}
            options={[
              { value: 'slow', label: 'Slow' },
              { value: 'normal', label: 'Normal' },
              { value: 'brisk', label: 'Brisk' },
            ]}
          />
          <p className="mt-2 text-2xs text-ink3">Synthetic input: new cycles run at ×1.15 / ×1.0 / ×0.85 of this operator's normal cycle time. Drives the ETA and the operator task planner's early/late view.</p>
        </div>
      )}
      {show('weather') && (
        <div>
          <div className="mb-2 text-sm font-medium text-ink2">Weather</div>
          <Segmented
            value={state?.weather || 'clear'}
            onChange={(v) => run('weather', v)}
            options={[
              { value: 'clear', label: 'Clear', icon: Cloud },
              { value: 'rain', label: 'Rain', icon: CloudRain },
              { value: 'heat', label: 'Heat', icon: Sun },
            ]}
          />
        </div>
      )}
      {err && <p className="text-xs text-crit">{err}</p>}
    </div>
  )
}
