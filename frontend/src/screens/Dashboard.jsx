import { Cloud, CloudRain, Fuel, Gauge, History, Hourglass, Link2, Link2Off, Navigation, Repeat, Sun, Thermometer, Weight, Wrench } from 'lucide-react'
import { Link } from 'react-router-dom'
import AlertQueue from '../components/AlertQueue'
import { AnomalyCompact } from '../components/AnomalyCard'
import EventList from '../components/EventList'
import ExplainPanel from '../components/ExplainPanel'
import { EtaCard, TaskList } from '../components/TaskCards'
import { Card, CardHeader, Chip, Source, Stat } from '../components/ui'
import { PHASE_LABEL, fmt } from '../lib/format'
import { useApp } from '../lib/store'
import Gate from './Gate'

const WEATHER_ICON = { clear: Cloud, rain: CloudRain, heat: Sun }

export default function Dashboard() {
  return <Gate what="tasks, ETAs and live machine state"><DashboardView /></Gate>
}

function DashboardView() {
  const { events } = useApp()
  return (
        <div className="space-y-5">
          <AlertQueue />
          <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
            <EtaCard />
            <MachineCard />
          </div>
          <div className="grid gap-5 xl:grid-cols-3">
            <TaskList />
            <div className="space-y-5">
              <AnomalyCompact />
              <ExplainPanel compact />
            </div>
            <Card>
              <CardHeader icon={History} title="Latest events" subtitle="Auto-logged by the rule engine and models"
                right={<Link to="/timeline" className="text-xs font-semibold text-ink3 hover:text-cat">All events →</Link>} />
              <EventList events={events.slice(0, 6)} compact />
            </Card>
          </div>
        </div>
  )
}

function MachineCard() {
  const { state, meta } = useApp()
  const W = WEATHER_ICON[state.weather] || Cloud
  const hot = state.hyd_temp > 75
  return (
    <Card>
      <CardHeader icon={Wrench} title="Machine" subtitle={`${state.machine_id} · live telemetry`}
        right={<Chip tone={state.idle ? 'anom' : 'cat'}>{PHASE_LABEL[state.phase] || state.phase}</Chip>} />
      <div className="grid grid-cols-2 gap-3 px-5 sm:grid-cols-3 xl:grid-cols-2 2xl:grid-cols-3">
        <Stat icon={Gauge} label="Engine" value={state.rpm} unit="rpm" />
        <Stat icon={Fuel} label="Fuel" value={fmt(state.fuel_pct)} unit="%" sub={`${fmt(state.fuel_rate_lph)} L/h burn`} tone={state.fuel_pct < 20 ? 'warn' : undefined} />
        <Stat icon={Thermometer} label="Hyd. oil" value={fmt(state.hyd_temp)} unit="°C" tone={hot ? 'warn' : undefined} />
        <Stat icon={Navigation} label="Travel" value={fmt(state.speed_kmh)} unit="km/h" sub={state.swing ? 'Swinging' : state.speed_kmh > 0 ? 'Tramming' : 'Stationary'} />
        <Stat icon={Weight} label="Last payload" flash value={fmt(state.payload_t)} unit="t" />
        <Stat icon={Repeat} label="Last cycle" flash value={fmt(state.cycle_s)} unit="s" />
        <Stat icon={Hourglass} label="Idle" flash value={fmt(state.idle_min)} unit="min" tone={state.anomaly?.flag && state.anomaly.type === 'excess_idle' ? 'anom' : undefined} sub={state.idle ? 'Machine idle' : 'Working'} />
        <Stat icon={state.seatbelt ? Link2 : Link2Off} label="Seatbelt" flash value={state.seatbelt ? 'On' : 'Off'} tone={state.seatbelt ? 'safe' : 'crit'} />
        <Stat icon={W} label="Weather" flash value={state.weather[0].toUpperCase() + state.weather.slice(1)} tone={state.weather === 'rain' ? 'warn' : undefined} />
      </div>
      <Source className="px-5 py-4">Simulated telemetry (synthetic) ticking once per second; fuel % derived from burn rate and a {meta?.fuel_tank_l} L tank.</Source>
    </Card>
  )
}
