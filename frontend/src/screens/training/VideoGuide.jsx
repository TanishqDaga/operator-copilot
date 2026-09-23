/**
 * Complete Video Guide
 *
 * Overview mode:
 * - Displays 3 sections (Level 1: Fundamentals, Level 2: Operations, Level 3: Advanced)
 * - Each section showcases exactly 3 active YouTube thumbnail preview cards
 * - Direct active YouTube link redirects (opens in new tab) + in-app details modal
 * - "View More Videos" button redirects to the complete stack view of all videos in that section
 *
 * Complete Stack mode (/training/video/:levelId):
 * - Displays all videos in that section with thumbnails, objectives, search, and completion tracking
 * - Back button returns to the main Video Guide overview
 */
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  Circle,
  Clock,
  ExternalLink,
  Layers,
  Play,
  RotateCcw,
  Search,
  Sparkles,
  Trophy,
  X,
} from 'lucide-react'
import { useCallback, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Card, CardHeader, Empty, Progress } from '../../components/ui'
import {
  extractYoutubeId,
  getAllLessons,
  getYoutubeThumbnail,
  VIDEO_GUIDE,
} from '../../data/videoGuide'

// ── localStorage progress helper ───────────────────────────────────────────

const STORAGE_KEY = 'cat_video_guide_progress'

function loadProgress() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveProgress(progress) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(progress))
  } catch { /* ignore */ }
}

// ── Difficulty Badge ────────────────────────────────────────────────────────

const DIFF = {
  beginner: { label: 'Beginner', cls: 'border-safe/30 bg-safe/10 text-safe' },
  intermediate: { label: 'Intermediate', cls: 'border-cat/30 bg-cat/10 text-cat' },
  advanced: { label: 'Advanced', cls: 'border-anom/40 bg-anom/10 text-anom' },
}

function DiffBadge({ difficulty }) {
  const d = DIFF[difficulty] || DIFF.beginner
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-2xs font-semibold ${d.cls}`}>
      {d.label}
    </span>
  )
}

// ── Video Card Component with YouTube Thumbnail ────────────────────────────

function VideoThumbnailCard({ lesson, done, onToggleComplete, onOpenDetails }) {
  const thumbUrl = getYoutubeThumbnail(lesson.youtube_url)
  const [imgError, setImgError] = useState(false)

  const handleWatch = (e) => {
    e.stopPropagation()
    if (lesson.youtube_url) {
      window.open(lesson.youtube_url, '_blank', 'noopener,noreferrer')
    } else {
      const searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(lesson.youtube_search)}`
      window.open(searchUrl, '_blank', 'noopener,noreferrer')
    }
  }

  return (
    <div
      className={`group relative flex flex-col overflow-hidden rounded-2xl border transition-all duration-200 hover:-translate-y-1 hover:shadow-lg ${
        done
          ? 'border-safe/30 bg-safe/[0.03] hover:border-safe/50'
          : 'border-line2 bg-panel hover:border-line hover:bg-raised/70'
      }`}
    >
      {/* ── 16:9 Thumbnail Preview Container ─────────────────────────────── */}
      <div
        className="relative aspect-video w-full overflow-hidden bg-black/60 cursor-pointer"
        onClick={handleWatch}
        title={`Watch "${lesson.title}" on YouTube`}
      >
        {thumbUrl && !imgError ? (
          <img
            src={thumbUrl}
            alt={lesson.title}
            onError={() => setImgError(true)}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel2 to-raised">
            <BookOpen size={32} className="text-ink3 opacity-40" />
          </div>
        )}

        {/* Gradient dark overlays */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />

        {/* YouTube logo pill on top-left */}
        <div className="absolute top-2.5 left-2.5 flex items-center gap-1 rounded-md bg-[#FF0000]/90 px-2 py-0.5 text-[11px] font-bold text-white shadow">
          <span>YouTube</span>
        </div>

        {/* Completed status on top-right */}
        {done && (
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1 rounded-md bg-safe/90 px-2 py-0.5 text-2xs font-bold text-white shadow">
            <Check size={11} strokeWidth={3} /> Done
          </div>
        )}

        {/* Central Play Button */}
        <div className="absolute inset-0 grid place-items-center">
          <div className="grid h-12 w-12 place-items-center rounded-full bg-black/70 border border-white/20 text-white shadow-xl backdrop-blur-sm transition-all duration-200 group-hover:scale-110 group-hover:bg-[#FF0000] group-hover:border-[#FF0000]">
            <Play size={20} className="ml-0.5 fill-current" />
          </div>
        </div>

        {/* Duration badge on bottom-right */}
        <div className="absolute bottom-2.5 right-2.5 flex items-center gap-1 rounded bg-black/85 px-1.5 py-0.5 text-2xs font-semibold text-white/90">
          <Clock size={10} /> {lesson.duration_min} min
        </div>
      </div>

      {/* ── Card Content ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <DiffBadge difficulty={lesson.difficulty} />
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleComplete(lesson.id)
            }}
            className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-2xs font-medium transition-colors ${
              done
                ? 'bg-safe/15 text-safe hover:bg-safe/25'
                : 'text-ink3 hover:text-ink hover:bg-raised'
            }`}
            title={done ? 'Mark as incomplete' : 'Mark as completed'}
          >
            {done ? <Check size={12} strokeWidth={2.5} /> : <Circle size={12} />}
            {done ? 'Completed' : 'Mark done'}
          </button>
        </div>

        {/* Lesson Title */}
        <h4
          className="text-sm font-bold text-ink leading-snug line-clamp-2 cursor-pointer hover:text-cat transition-colors"
          onClick={handleWatch}
          title={lesson.title}
        >
          {lesson.title}
        </h4>

        {/* Short description */}
        <p className="mt-1.5 text-xs text-ink3 line-clamp-2 leading-relaxed">
          {lesson.description}
        </p>

        {/* Actions row */}
        <div className="mt-4 flex items-center justify-between gap-2 pt-3 border-t border-line/60">
          <button
            onClick={handleWatch}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-cat hover:text-cat-hover transition-colors"
          >
            <Play size={12} className="fill-current" />
            Watch Video
            <ExternalLink size={11} className="opacity-70" />
          </button>

          <button
            onClick={() => onOpenDetails(lesson)}
            className="text-2xs font-medium text-ink3 hover:text-ink hover:underline transition-colors"
          >
            Objectives →
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Lesson Details Modal ───────────────────────────────────────────────────

function LessonModal({ lesson, completed, onToggleComplete, onClose }) {
  if (!lesson) return null

  const handleWatch = () => {
    if (lesson.youtube_url) {
      window.open(lesson.youtube_url, '_blank', 'noopener,noreferrer')
    } else {
      const searchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(lesson.youtube_search)}`
      window.open(searchUrl, '_blank', 'noopener,noreferrer')
    }
  }

  const thumbUrl = getYoutubeThumbnail(lesson.youtube_url)

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <div className="absolute inset-0 bg-black/75 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-xl card p-0 animate-rise overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-start justify-between gap-4 bg-raised px-6 pt-5 pb-4 border-b border-line">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <DiffBadge difficulty={lesson.difficulty} />
              <span className="text-2xs text-ink3 flex items-center gap-1">
                <Clock size={11} /> {lesson.duration_min} min
              </span>
            </div>
            <h2 className="text-xl font-bold text-ink leading-tight">{lesson.title}</h2>
          </div>
          <button
            className="shrink-0 rounded-lg p-1.5 text-ink3 hover:text-ink hover:bg-panel transition-colors"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Active Video Preview Link */}
          <div
            className="group relative aspect-video w-full overflow-hidden rounded-xl bg-black cursor-pointer shadow-md"
            onClick={handleWatch}
          >
            {thumbUrl && (
              <img
                src={thumbUrl}
                alt={lesson.title}
                className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105 opacity-80"
              />
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent" />
            <div className="absolute inset-0 grid place-items-center">
              <div className="flex items-center gap-2 rounded-xl bg-[#FF0000] px-4 py-2.5 font-bold text-white shadow-xl transition-transform duration-200 group-hover:scale-105">
                <Play size={18} className="fill-current" />
                <span>Watch on YouTube</span>
                <ExternalLink size={14} />
              </div>
            </div>
          </div>

          {/* Description */}
          <div>
            <div className="label mb-1">Description</div>
            <p className="text-sm text-ink leading-relaxed">{lesson.description}</p>
          </div>

          {/* Learning objective */}
          <div className="rounded-xl border border-cat/25 bg-cat/5 p-4">
            <div className="label text-cat font-semibold">Key Learning Objective</div>
            <p className="mt-1 text-sm text-ink leading-relaxed">{lesson.objective}</p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between gap-3 border-t border-line bg-raised px-6 py-4">
          <button className="btn btn-ghost btn-md" onClick={onClose}>
            Close
          </button>
          <div className="flex items-center gap-2">
            <button
              className={`btn btn-md ${completed ? 'btn-ghost' : 'btn-primary'}`}
              onClick={() => {
                onToggleComplete(lesson.id)
                onClose()
              }}
            >
              {completed ? (
                <>
                  <Circle size={16} /> Mark as not done
                </>
              ) : (
                <>
                  <Check size={16} /> Mark as complete
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Complete Stack View for a Single Section ────────────────────────────────

function CompleteStackView({ level, progress, onToggleComplete, onOpenDetails, onBack }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // all, completed, incomplete

  const filteredLessons = useMemo(() => {
    return level.lessons.filter((l) => {
      const matchSearch =
        !search.trim() ||
        l.title.toLowerCase().includes(search.toLowerCase()) ||
        l.description.toLowerCase().includes(search.toLowerCase())
      const isDone = !!progress[l.id]
      if (!matchSearch) return false
      if (filter === 'completed') return isDone
      if (filter === 'incomplete') return !isDone
      return true
    })
  }, [level.lessons, search, filter, progress])

  const completedCount = level.lessons.filter((l) => progress[l.id]).length
  const total = level.lessons.length
  const pct = total > 0 ? completedCount / total : 0

  return (
    <div className="space-y-5 animate-rise">
      {/* ── Navigation & Header ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          onClick={onBack}
          className="inline-flex items-center gap-2 rounded-xl border border-line bg-panel px-3.5 py-2 text-sm font-semibold text-ink2 hover:border-cat/40 hover:bg-raised hover:text-ink transition-colors"
        >
          <ArrowLeft size={16} />
          Back to All Sections
        </button>

        <div className="flex items-center gap-2">
          <span className="text-xs text-ink3">Completion:</span>
          <span className="rounded-lg border border-cat/30 bg-cat/10 px-2.5 py-1 text-xs font-bold text-cat">
            {completedCount} of {total} completed ({Math.round(pct * 100)}%)
          </span>
        </div>
      </div>

      {/* Level Banner Card */}
      <Card className="overflow-hidden border-cat/25 bg-gradient-to-r from-cat/[0.07] via-panel to-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl border border-line bg-panel2 text-3xl shadow">
              {level.icon}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-md border border-line bg-raised px-2 py-0.5 text-2xs font-bold uppercase tracking-wider text-ink3">
                  Full Curriculum Stack
                </span>
                <span className="text-2xs font-semibold text-ink3">· {total} Total Videos</span>
              </div>
              <h2 className="mt-1 text-2xl font-bold text-ink">{level.title}</h2>
              <p className="mt-1 text-sm text-ink2">{level.subtitle}</p>
            </div>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-3">
          <Progress value={pct} tone="cat" className="flex-1 h-2.5" />
          <span className="num text-sm font-bold text-cat">{Math.round(pct * 100)}%</span>
        </div>
      </Card>

      {/* ── Search & Filter Controls ────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[240px] flex-1 sm:max-w-md">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-ink3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search within ${level.title}...`}
            className="w-full rounded-xl border border-line bg-panel pl-9 pr-4 py-2 text-sm text-ink placeholder:text-ink3 focus:border-cat/60 focus:outline-none"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink3 hover:text-ink"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Status filters */}
        <div className="flex items-center gap-1.5 rounded-xl border border-line bg-panel p-1">
          <button
            onClick={() => setFilter('all')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'all'
                ? 'bg-cat/20 text-cat'
                : 'text-ink3 hover:text-ink'
            }`}
          >
            All ({total})
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'completed'
                ? 'bg-safe/20 text-safe'
                : 'text-ink3 hover:text-ink'
            }`}
          >
            Completed ({completedCount})
          </button>
          <button
            onClick={() => setFilter('incomplete')}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
              filter === 'incomplete'
                ? 'bg-cat/20 text-cat'
                : 'text-ink3 hover:text-ink'
            }`}
          >
            To Watch ({total - completedCount})
          </button>
        </div>
      </div>

      {/* ── Complete Stack Video Grid ───────────────────────────────────── */}
      {filteredLessons.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredLessons.map((lesson) => (
            <VideoThumbnailCard
              key={lesson.id}
              lesson={lesson}
              done={!!progress[lesson.id]}
              onToggleComplete={onToggleComplete}
              onOpenDetails={onOpenDetails}
            />
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <Empty icon={Search} title="No videos match your filter">
            Try adjusting your search keywords or toggle between All / To Watch.
          </Empty>
        </Card>
      )}
    </div>
  )
}

// ── Overview Section with Exactly 3 Featured Thumbnail Cards ───────────────

function SectionOverview({ level, progress, onToggleComplete, onOpenDetails, onViewMore }) {
  const completedCount = level.lessons.filter((l) => progress[l.id]).length
  const total = level.lessons.length
  const pct = total > 0 ? completedCount / total : 0

  // Exactly 3 featured videos
  const previewLessons = level.lessons.slice(0, 3)
  const remainingCount = total - previewLessons.length

  return (
    <Card className="overflow-hidden border-line2 bg-panel p-5">
      {/* ── Section Header ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-line/70">
        <div className="flex items-center gap-3.5">
          <div className="grid h-12 w-12 place-items-center rounded-xl border border-line bg-raised text-2xl shadow-sm">
            {level.icon}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-ink">{level.title}</h3>
              <span className="rounded-md border border-line bg-raised px-2 py-0.5 text-2xs font-semibold text-ink2">
                {completedCount}/{total} complete
              </span>
            </div>
            <p className="mt-0.5 text-xs text-ink3">{level.subtitle}</p>
          </div>
        </div>

        {/* Progress gauge */}
        <div className="flex items-center gap-3">
          <Progress value={pct} tone="cat" className="w-28 h-2" />
          <span className="text-xs font-semibold text-ink2 num">{Math.round(pct * 100)}%</span>
        </div>
      </div>

      {/* ── Exactly Three YouTube Video Thumbnail Previews ────────────── */}
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {previewLessons.map((lesson) => (
          <VideoThumbnailCard
            key={lesson.id}
            lesson={lesson}
            done={!!progress[lesson.id]}
            onToggleComplete={onToggleComplete}
            onOpenDetails={onOpenDetails}
          />
        ))}
      </div>

      {/* ── View More Videos Button (Redirecting to Complete Stack) ───── */}
      <div className="mt-5 flex items-center justify-center pt-3 border-t border-line/50">
        <button
          onClick={() => onViewMore(level.id)}
          className="inline-flex items-center gap-2 rounded-xl border border-cat/30 bg-cat/10 px-5 py-2.5 text-sm font-semibold text-cat hover:border-cat/60 hover:bg-cat/20 hover:shadow-md transition-all duration-150"
        >
          <Layers size={16} />
          <span>View More Videos</span>
          <span className="rounded-md bg-cat/20 px-1.5 py-0.5 text-2xs font-bold">
            +{remainingCount} more
          </span>
          <ArrowRight size={15} />
        </button>
      </div>
    </Card>
  )
}

// ── Main VideoGuide Screen ──────────────────────────────────────────────────

export default function VideoGuide() {
  const { levelId } = useParams()
  const navigate = useNavigate()
  const [progress, setProgress] = useState(loadProgress)
  const [activeLesson, setActiveLesson] = useState(null)

  const toggleComplete = useCallback((lessonId) => {
    setProgress((prev) => {
      const next = { ...prev, [lessonId]: !prev[lessonId] }
      saveProgress(next)
      return next
    })
  }, [])

  // Overall Stats
  const allLessons = useMemo(() => getAllLessons(), [])
  const totalLessons = allLessons.length
  const completedTotal = allLessons.filter((l) => progress[l.id]).length
  const overallPct = totalLessons > 0 ? completedTotal / totalLessons : 0

  // Check if a specific level stack is selected via URL param
  const activeLevel = useMemo(() => {
    if (!levelId) return null
    return VIDEO_GUIDE.find((lvl) => lvl.id === levelId) || null
  }, [levelId])

  // Continue Learning quick pick
  const nextLesson = useMemo(() => {
    for (const level of VIDEO_GUIDE) {
      for (const lesson of level.lessons) {
        if (!progress[lesson.id]) return lesson
      }
    }
    return null
  }, [progress])

  return (
    <div className="space-y-6">
      {/* ── Header Summary Bar ───────────────────────────────────────── */}
      <Card className="p-5 border-line bg-panel shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-md border border-cat/30 bg-cat/10 px-2 py-0.5 text-2xs font-semibold text-cat">
                <Sparkles size={11} /> 3-Level Operator Curriculum
              </span>
              <span className="text-2xs text-ink3">· 40 Verified Video Lessons</span>
            </div>
            <h2 className="mt-1 text-xl font-bold text-ink">Complete Video Guide</h2>
            <p className="mt-0.5 text-xs text-ink3">
              Master machine fundamentals, production excavation cycles, and Next Gen Caterpillar technologies.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {completedTotal === totalLessons ? (
              <div className="flex items-center gap-2 rounded-xl border border-safe/30 bg-safe/10 px-4 py-2 text-safe">
                <Trophy size={18} />
                <span className="text-sm font-semibold">All 40 Lessons Complete!</span>
              </div>
            ) : nextLesson ? (
              <button
                className="btn btn-primary btn-sm flex items-center gap-1.5"
                onClick={() => {
                  if (nextLesson.youtube_url) {
                    window.open(nextLesson.youtube_url, '_blank', 'noopener,noreferrer')
                  } else {
                    setActiveLesson(nextLesson)
                  }
                }}
              >
                <Play size={14} className="fill-current" /> Continue Learning
              </button>
            ) : null}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4 flex items-center gap-3">
          <Progress value={overallPct} tone="cat" className="flex-1 h-2" />
          <span className="num text-xs font-bold text-cat">
            {completedTotal} / {totalLessons} ({Math.round(overallPct * 100)}%)
          </span>
        </div>
      </Card>

      {/* ── Mode 1: Complete Stack View for a Selected Section ───────── */}
      {activeLevel ? (
        <CompleteStackView
          level={activeLevel}
          progress={progress}
          onToggleComplete={toggleComplete}
          onOpenDetails={setActiveLesson}
          onBack={() => navigate('/training/video')}
        />
      ) : (
        /* ── Mode 2: Three Sections with Exactly 3 YouTube Previews Each ── */
        <div className="space-y-6">
          {VIDEO_GUIDE.map((level) => (
            <SectionOverview
              key={level.id}
              level={level}
              progress={progress}
              onToggleComplete={toggleComplete}
              onOpenDetails={setActiveLesson}
              onViewMore={(lvlId) => navigate(`/training/video/${lvlId}`)}
            />
          ))}
        </div>
      )}

      {/* ── Video Details / Objective Modal ──────────────────────────── */}
      {activeLesson && (
        <LessonModal
          lesson={activeLesson}
          completed={!!progress[activeLesson.id]}
          onToggleComplete={toggleComplete}
          onClose={() => setActiveLesson(null)}
        />
      )}
    </div>
  )
}
