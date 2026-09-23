import { FlaskConical, X } from 'lucide-react'
import { useEffect } from 'react'
import { useApp } from '../lib/store'
import { MachineControls, PersonControls } from './SimControls'
import { SyntheticTag } from './ui'

export default function SimDrawer() {
  const { simOpen, setSimOpen, active } = useApp()
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && setSimOpen(false)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [setSimOpen])
  if (!simOpen) return null
  return (
    <div className="fixed inset-0 z-50 no-print">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={() => setSimOpen(false)} />
      <aside className="absolute right-0 top-0 flex h-full w-full max-w-[400px] flex-col border-l border-line2 bg-panel animate-slideIn">
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-cat/10 text-cat"><FlaskConical size={18} /></span>
            <div>
              <div className="font-semibold text-ink">Simulation inputs</div>
              <div className="text-2xs text-ink3">Drive the live shift for demo and testing</div>
            </div>
          </div>
          <button className="btn btn-quiet h-10 w-10" onClick={() => setSimOpen(false)} aria-label="Close"><X size={18} /></button>
        </header>
        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <SyntheticTag />
          {!active ? (
            <p className="text-sm text-ink3">Start the shift to use simulation inputs.</p>
          ) : (
            <>
              <section>
                <div className="label mb-3">Person near machine</div>
                <PersonControls />
              </section>
              <section>
                <div className="label mb-3">Machine & site</div>
                <MachineControls />
              </section>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
