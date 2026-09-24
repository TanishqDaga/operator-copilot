import { BookOpen, Bot, Sparkles } from 'lucide-react'
import { NavLink, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { PageHeader } from '../../components/ui'
import Gate from '../Gate'
import AIAssistant from './AIAssistant'
import RecommendedTraining from './RecommendedTraining'
import VideoGuide from './VideoGuide'

const TABS = [
  { to: '/training', end: true, label: 'Recommended Training', icon: Sparkles },
  { to: '/training/video', end: false, label: 'Complete Video Guide', icon: BookOpen },
  { to: '/training/assistant', end: false, label: 'AI Assistant', icon: Bot },
]

function TrainingTabs() {
  return (
    <div className="mb-5 flex flex-wrap items-center gap-2">
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end}
          className={({ isActive }) =>
            `inline-flex items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition-all duration-150 ${
              isActive
                ? 'border-cat bg-cat text-cat-ink shadow-sm'
                : 'border-line2 bg-raised text-ink2 hover:border-line2 hover:bg-raised hover:text-ink'
            }`
          }
        >
          <t.icon size={15} />
          {t.label}
        </NavLink>
      ))}
    </div>
  )
}

export default function TrainingHub() {
  return (
    <Gate allowEnded what="training">
      <PageHeader
        title="Training Hub"
        subtitle="Coaching from today's events · Complete video curriculum · AI assistant"
      />
      <TrainingTabs />
      <Routes>
        <Route index element={<RecommendedTraining />} />
        <Route path="video" element={<VideoGuide />} />
        <Route path="video/:levelId" element={<VideoGuide />} />
        <Route path="assistant" element={<AIAssistant />} />
      </Routes>
    </Gate>
  )
}
