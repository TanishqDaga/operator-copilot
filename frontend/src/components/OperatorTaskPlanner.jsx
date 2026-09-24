import { Clock3, Compass } from 'lucide-react'
import { useApp } from '../lib/store'
import CurrentTaskExecution from './CurrentTaskExecution'
import NextBestAction from './NextBestAction'
import ProductivityMetrics from './ProductivityMetrics'
import TaskPreparationCard from './TaskPreparationCard'
import UpcomingTasks from './UpcomingTasks'
import WeatherGuidance from './WeatherGuidance'
import { Card, CardHeader, Chip, Empty } from './ui'

/**
 * Operator Task Planner — how to execute the manager's published schedule well.
 * Read-only: it never reorders, reassigns or republishes anything.
 */
export default function OperatorTaskPlanner() {
  const { operatorPlan: p } = useApp()
  if (!p) return null
  if (!p.available) {
    return (
      <Card>
        <CardHeader icon={Compass} title="Operator task planner" subtitle="Execution guidance for your published schedule" />
        <Empty icon={Compass} title={p.message}>The planner only guides execution of the manager's published schedule; it never creates one.</Empty>
      </Card>
    )
  }
  const hold = p.safety_priority?.active
  const clock = p.schedule_clock
  return (
    <Card className={hold ? 'border-crit/50' : ''}>
      <CardHeader icon={Compass} title="Operator task planner"
        subtitle={`Execution guidance for ${p.schedule_id} · ${p.tasks_completed}/${p.tasks_total} of your tasks done`}
        right={
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
            <Chip tone={hold ? 'crit' : 'cat'} className="!py-0.5 !text-2xs">{p.state.label}</Chip>
            {clock?.now && (
              <span className="num inline-flex items-center gap-1 text-2xs text-ink3" title={clock.note}>
                <Clock3 size={12} /> schedule {clock.now} · live {clock.live_clock?.slice(0, 5)} · ×{clock.compression}
              </span>
            )}
          </div>
        } />
      <div className="space-y-4 px-5">
        {/* weather items have their own panel; while safety holds, everything deferred is listed here */}
        <NextBestAction nba={p.next_best_action} state={p.state}
          secondary={hold ? p.secondary_actions : p.secondary_actions.filter((a) => a.category !== 'WEATHER')} />
        <div className={`grid gap-4 lg:grid-cols-2 ${hold ? 'opacity-60' : ''}`}>
          <CurrentTaskExecution task={p.current_task} state={p.state} />
          <TaskPreparationCard task={p.next_task} live={p.live} />
        </div>
        <div className={`grid gap-4 lg:grid-cols-3 ${hold ? 'opacity-60' : ''}`}>
          <UpcomingTasks tasks={p.upcoming_tasks} />
          <WeatherGuidance weather={p.weather_guidance} />
          <ProductivityMetrics p={p.productivity} />
        </div>
      </div>
    </Card>
  )
}
