import { History } from 'lucide-react'
import { useMemo, useState } from 'react'
import EventList from '../components/EventList'
import { Card, Empty, PageHeader, Segmented } from '../components/ui'
import { useApp } from '../lib/store'
import Gate from './Gate'

const FILTERS = {
  all: () => true,
  safety: (e) => e.kind === 'safety' || e.kind === 'seatbelt' || e.kind === 'notice',
  anomaly: (e) => e.kind === 'anomaly',
  eta: (e) => e.kind === 'eta' || e.kind === 'task',
  other: (e) => ['weather', 'sim', 'shift', 'training'].includes(e.kind),
}

export default function Timeline() {
  const { events } = useApp()
  const [f, setF] = useState('all')
  const list = useMemo(() => events.filter(FILTERS[f]), [events, f])
  const count = (k) => events.filter(FILTERS[k]).length
  const crit = events.filter((e) => e.kind === 'safety' && e.level === 'CRITICAL').length
  const warn = events.filter((e) => e.kind === 'safety' && e.level === 'WARNING').length
  const anom = events.filter((e) => e.kind === 'anomaly' && e.level === 'ANOMALY').length
  return (
    <Gate allowEnded what="the event timeline">
      <PageHeader title="Event timeline" subtitle="Every safety level change, anomaly, ETA change and site event — logged automatically, newest first." />
      <div className="mb-5 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Tile label="Critical" value={crit} tone="text-crit" />
        <Tile label="Warning" value={warn} tone="text-warn" />
        <Tile label="Anomalies" value={anom} tone="text-anom" />
        <Tile label="Total events" value={events.length} tone="text-ink" />
      </div>
      <Card>
        <div className="border-b border-line p-3 md:max-w-2xl">
          <Segmented value={f} onChange={setF} options={[
            { value: 'all', label: `All ${count('all')}` },
            { value: 'safety', label: `Safety ${count('safety')}` },
            { value: 'anomaly', label: `Anomaly ${count('anomaly')}` },
            { value: 'eta', label: `ETA ${count('eta')}` },
            { value: 'other', label: `Other ${count('other')}` },
          ]} />
        </div>
        <div className="p-5">
          {list.length ? <EventList events={list} /> : <Empty icon={History} title="Nothing here yet">Events appear here the moment the rule engine or a model raises them.</Empty>}
        </div>
      </Card>
    </Gate>
  )
}

function Tile({ label, value, tone }) {
  return (
    <div className="card px-4 py-3">
      <div className="label">{label}</div>
      <div className={`num mt-1 text-3xl font-semibold ${tone}`}>{value}</div>
    </div>
  )
}
