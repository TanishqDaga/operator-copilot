import {
  Activity, ChevronRight, ClipboardCheck, FileText, FlaskConical, GraduationCap, History, LayoutDashboard,
  OctagonAlert, ShieldAlert, TriangleAlert, Wifi, WifiOff, X,
} from 'lucide-react'
import { useEffect } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LEVEL, REASON_LABEL } from '../lib/format'
import { useApp } from '../lib/store'
import ErrorBoundary from './ErrorBoundary'
import SimDrawer from './SimDrawer'
import { LevelPill, SyntheticTag } from './ui'

const NAV = [
  { to: '/start', label: 'Shift start', icon: ClipboardCheck },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/safety', label: 'Safety', icon: ShieldAlert, key: 'safety' },
  { to: '/timeline', label: 'Event timeline', icon: History, key: 'timeline' },
  { to: '/anomaly', label: 'Anomaly', icon: Activity, key: 'anomaly' },
  { to: '/training', label: 'Training', icon: GraduationCap },
  { to: '/summary', label: 'Shift summary', icon: FileText },
]

const TITLES = {
  '/start': 'Shift start', '/dashboard': 'Dashboard', '/safety': 'Safety', '/timeline': 'Event timeline',
  '/anomaly': 'Anomaly', '/training': 'Training hub', '/summary': 'Shift summary & handoff',
}

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <svg viewBox="0 0 32 32" className="h-9 w-9 shrink-0">
        <path d="M16 2l12 7v14l-12 7-12-7V9z" fill="#FFCD11" />
        <path d="M16 9l6 3.5v7L16 23l-6-3.5v-7z" fill="#0A0C0F" />
      </svg>
      <div className="leading-tight">
        <div className="text-[15px] font-extrabold tracking-tight text-ink">Operator Copilot</div>
        <div className="text-2xs font-semibold uppercase tracking-[0.16em] text-cat">CAT in-cab assistant</div>
      </div>
    </div>
  )
}

function useBadges() {
  const { state, events } = useApp()
  const level = state?.safety?.level || 'SAFE'
  return {
    safety: level !== 'SAFE' ? <span className={`h-2.5 w-2.5 rounded-full ${LEVEL[level].bg} ${level === 'CRITICAL' ? 'animate-pulse' : ''}`} /> : null,
    anomaly: state?.anomaly?.flag ? <span className="h-2.5 w-2.5 rounded-full bg-anom" /> : null,
    timeline: events.length ? <span className="num rounded-md bg-raised px-1.5 text-2xs text-ink2">{events.length}</span> : null,
  }
}

function Sidebar() {
  const { meta } = useApp()
  const badges = useBadges()
  return (
    <aside className="no-print sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col border-r border-line bg-[#0C0F13] lg:flex">
      <div className="px-5 py-5"><Logo /></div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            className={({ isActive }) =>
              `group flex h-12 items-center gap-3 rounded-xl px-3 text-[14px] font-medium transition-colors ${
                isActive ? 'bg-raised text-ink shadow-[inset_3px_0_0_0_#FFCD11]' : 'text-ink3 hover:bg-panel hover:text-ink2'
              }`
            }
          >
            <n.icon size={18} />
            <span className="flex-1">{n.label}</span>
            {n.key && badges[n.key]}
          </NavLink>
        ))}
      </nav>
      <div className="m-3 space-y-2 rounded-xl border border-line bg-panel p-3">
        <SyntheticTag />
        <p className="text-2xs leading-4 text-ink3">
          No live machine data connected. Telemetry, history and models are generated from a synthetic dataset.
        </p>
        {meta?.eta && (
          <p className="text-2xs leading-4 text-ink3 num">
            ETA model MAE {meta.eta.mae_min} min · n={meta.eta.n_test} held-out
          </p>
        )}
      </div>
    </aside>
  )
}

function MobileNav() {
  const badges = useBadges()
  return (
    <nav className="no-print fixed inset-x-0 bottom-0 z-40 flex overflow-x-auto border-t border-line bg-[#0C0F13]/95 backdrop-blur lg:hidden">
      {NAV.map((n) => (
        <NavLink key={n.to} to={n.to}
          className={({ isActive }) => `relative flex min-w-[76px] flex-1 flex-col items-center gap-1 py-2.5 text-[10px] font-semibold ${isActive ? 'text-cat' : 'text-ink3'}`}>
          <n.icon size={20} />
          {n.label.split(' ')[0]}
          {n.key && badges[n.key] && <span className="absolute right-4 top-2">{badges[n.key]}</span>}
        </NavLink>
      ))}
    </nav>
  )
}

function TopBar() {
  const { state, online, setSimOpen, active } = useApp()
  const { pathname } = useLocation()
  const sh = state?.shift || {}
  return (
    <header className="no-print sticky top-0 z-30 border-b border-line bg-bg/85 backdrop-blur-md">
      <div className="flex h-16 items-center gap-4 px-4 md:px-6">
        <div className="lg:hidden"><svg viewBox="0 0 32 32" className="h-8 w-8"><path d="M16 2l12 7v14l-12 7-12-7V9z" fill="#FFCD11" /><path d="M16 9l6 3.5v7L16 23l-6-3.5v-7z" fill="#0A0C0F" /></svg></div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-semibold text-ink">{TITLES[pathname] || 'Operator Copilot'}</div>
          <div className="truncate text-2xs text-ink3">
            {state?.machine_id} {sh.operator_name ? `· ${sh.operator_name} (${state.operator_id})` : '· no operator signed in'}
            {state?.task ? ` · ${state.task.id} ${state.task.name}` : ''}
          </div>
        </div>
        <div className="hidden items-center gap-5 md:flex">
          <div className="text-right">
            <div className="label">Sim clock</div>
            <div className="num text-lg font-semibold leading-tight text-ink">{state?.ts || '--:--:--'}</div>
          </div>
          {sh.sim_offset_min > 0 && (
            <div className="text-right">
              <div className="label">Fast-forward</div>
              <div className="num text-sm text-ink2">+{sh.sim_offset_min} min</div>
            </div>
          )}
        </div>
        {active && <LevelPill level={state?.safety?.level || 'SAFE'} />}
        <span className={`hidden sm:inline-flex items-center gap-1.5 text-2xs font-semibold ${online ? 'text-safe' : 'text-crit'}`} title="GET /api/state every 1 s">
          {online ? <Wifi size={14} /> : <WifiOff size={14} />} {online ? 'Live · 1 s' : 'Offline'}
        </span>
        <button className="btn btn-ghost btn-md" onClick={() => setSimOpen(true)}>
          <FlaskConical size={16} /> <span className="hidden sm:inline">Simulate</span>
        </button>
      </div>
      <AlertBar />
    </header>
  )
}

function AlertBar() {
  const { state, active } = useApp()
  const { pathname } = useLocation()
  const s = state?.safety
  if (!active || !s || s.level === 'SAFE' || pathname === '/safety') return null
  const crit = s.level === 'CRITICAL'
  const Icon = crit ? OctagonAlert : TriangleAlert
  return (
    <Link to="/safety" key={s.level}
      className={`flex items-center gap-3 px-4 md:px-6 py-2.5 text-sm font-semibold animate-rise ${crit ? 'bg-crit text-white' : 'bg-warn text-[#1f1000]'}`}>
      <Icon size={18} className={crit ? 'animate-pulse' : ''} />
      <span className="uppercase tracking-wider">{s.level}</span>
      <span className="truncate font-medium opacity-90">{s.reasons.map((r) => REASON_LABEL[r] || r).join(' · ')} — {s.details[0]}</span>
      <ChevronRight size={16} className="ml-auto shrink-0" />
    </Link>
  )
}

const TOAST_STYLE = {
  CRITICAL: 'border-crit/60 text-crit', WARNING: 'border-warn/60 text-warn', SAFE: 'border-safe/50 text-safe',
  ANOMALY: 'border-anom/50 text-anom', INFO: 'border-info/40 text-info',
}

function Toasts() {
  const { toasts, dismissToast } = useApp()
  const nav = useNavigate()
  return (
    <div className="no-print fixed bottom-20 right-4 z-40 flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2 lg:bottom-5">
      {toasts.map((t) => (
        <div key={t.key} className={`animate-slideIn rounded-xl border bg-panel/95 p-3 shadow-2xl backdrop-blur ${TOAST_STYLE[t.level] || TOAST_STYLE.INFO}`}>
          <div className="flex items-start gap-3">
            <button className="min-w-0 flex-1 text-left" onClick={() => { dismissToast(t.key); nav('/timeline') }}>
              <div className="flex items-center gap-2 text-2xs font-bold uppercase tracking-wider">
                {t.kind} <span className="num font-medium text-ink3">{t.ts}</span>
              </div>
              <div className="mt-0.5 text-sm font-medium text-ink line-clamp-2">{t.title}</div>
            </button>
            <button className="text-ink3 hover:text-ink" onClick={() => dismissToast(t.key)} aria-label="Dismiss"><X size={16} /></button>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function Shell() {
  const { state } = useApp()
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  const crit = state?.shift?.active && state?.safety?.level === 'CRITICAL'
  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      <div className="relative flex min-w-0 flex-1 flex-col">
        {crit && <div className="pointer-events-none fixed inset-0 z-20 animate-critGlow shadow-[inset_0_0_0_3px_rgba(255,77,79,0.8),inset_0_0_80px_rgba(255,77,79,0.25)] no-print" />}
        <TopBar />
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 pb-28 pt-6 md:px-6 lg:pb-10">
          <ErrorBoundary resetKey={pathname}><Outlet /></ErrorBoundary>
        </main>
      </div>
      <MobileNav />
      <Toasts />
      <SimDrawer />
    </div>
  )
}
