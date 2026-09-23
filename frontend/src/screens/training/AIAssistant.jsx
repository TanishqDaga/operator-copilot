/**
 * AI Training Assistant — RAG-powered chat interface.
 * Posts to POST / (isolated backend endpoint).
 * Shows retrieved source citations under each AI response.
 */
import {
  AlertCircle,
  Bot,
  ChevronDown,
  ChevronUp,
  Database,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  User,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Card, CardHeader } from '../../components/ui'
import { api } from '../../lib/api'
import { useApp } from '../../lib/store'

// ── Suggested questions ─────────────────────────────────────────────────────

const SUGGESTED = [
  'Why could hydraulic temperature be increasing?',
  'How do I reduce excessive idle time?',
  'What should I check before working on wet ground?',
  'How can I improve my excavation cycle time?',
  'What should I do if a person enters the proximity zone?',
  'Create a 7-day plan to improve my excavation productivity.',
  'What causes slow excavation cycles?',
  'How do I safely operate on slopes?',
]

// ── Source Citation Component ───────────────────────────────────────────────

function SourcePanel({ sources, sourceType }) {
  const [open, setOpen] = useState(false)

  if (!sources || sources.length === 0) return null

  return (
    <div className="mt-3">
      <button
        className="flex items-center gap-1.5 text-2xs font-semibold text-ink3 hover:text-ink transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <Database size={11} />
        {sources.length} source{sources.length !== 1 ? 's' : ''} retrieved
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {open && (
        <div className="mt-2 space-y-2">
          {sources.map((src) => (
            <div
              key={src.id}
              className="rounded-lg border border-line bg-panel2 px-3 py-2.5"
            >
              <div className="flex items-start gap-2">
                <span className="num shrink-0 mt-0.5 grid h-4 w-4 place-items-center rounded bg-raised text-2xs font-bold text-ink3">
                  {src.id}
                </span>
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-ink">{src.title}</div>
                  <div className="text-2xs text-ink3">{src.section}</div>
                  <p className="mt-1 text-2xs text-ink3 leading-relaxed line-clamp-3">{src.excerpt}</p>
                </div>
              </div>
            </div>
          ))}
          {sourceType === 'template' && (
            <p className="text-2xs text-ink3 italic">
              Answer generated from retrieved documentation. LLM not available — connect an API key for richer responses.
            </p>
          )}
          {sourceType === 'llm' && (
            <p className="text-2xs text-ink3">
              ✓ Answer grounded in retrieved documentation via AI.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Message Bubble ──────────────────────────────────────────────────────────

function UserBubble({ text }) {
  return (
    <div className="flex justify-end">
      <div className="flex items-end gap-2 max-w-[85%]">
        <div className="rounded-2xl rounded-br-sm bg-cat/15 border border-cat/20 px-4 py-3">
          <p className="text-sm text-ink leading-relaxed">{text}</p>
        </div>
        <div className="shrink-0 grid h-8 w-8 place-items-center rounded-xl bg-cat/20 border border-cat/30">
          <User size={14} className="text-cat" />
        </div>
      </div>
    </div>
  )
}

function AssistantBubble({ message }) {
  const { answer, sources, source_type, note } = message

  return (
    <div className="flex justify-start">
      <div className="flex items-end gap-2 max-w-[92%] w-full">
        <div className="shrink-0 grid h-8 w-8 place-items-center rounded-xl bg-anom/15 border border-anom/30">
          <Bot size={14} className="text-anom" />
        </div>
        <div className="flex-1 rounded-2xl rounded-bl-sm border border-line bg-panel2 px-4 py-3">
          <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{answer}</p>
          {note && (
            <p className="mt-2 text-2xs text-ink3 italic">{note}</p>
          )}
          <SourcePanel sources={sources} sourceType={source_type} />
        </div>
      </div>
    </div>
  )
}

function ErrorBubble({ error, onRetry }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-end gap-2 max-w-[85%]">
        <div className="shrink-0 grid h-8 w-8 place-items-center rounded-xl bg-crit/15 border border-crit/30">
          <AlertCircle size={14} className="text-crit" />
        </div>
        <div className="rounded-2xl rounded-bl-sm border border-crit/20 bg-crit/5 px-4 py-3">
          <p className="text-sm text-crit">Unable to get a response. {error}</p>
          {onRetry && (
            <button
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-semibold text-crit hover:text-ink transition-colors"
              onClick={onRetry}
            >
              <RotateCcw size={12} /> Retry
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Empty / welcome state ───────────────────────────────────────────────────

function WelcomeState({ onAsk }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
      <div className="grid h-16 w-16 place-items-center rounded-2xl border border-anom/30 bg-anom/10 mb-4">
        <Bot size={28} className="text-anom" />
      </div>
      <h3 className="text-base font-bold text-ink">AI Training Assistant</h3>
      <p className="mt-2 max-w-md text-sm text-ink3">
        Ask anything about machine operation, safety, troubleshooting, or productivity.
        Answers are grounded in the operator training knowledge base.
      </p>
      <div className="mt-6 grid gap-2 sm:grid-cols-2 max-w-2xl w-full">
        {SUGGESTED.slice(0, 6).map((q) => (
          <button
            key={q}
            onClick={() => onAsk(q)}
            className="rounded-xl border border-line bg-panel2 px-4 py-3 text-sm text-ink2 text-left hover:border-line2 hover:bg-raised hover:text-ink transition-all"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Shift context badge ─────────────────────────────────────────────────────

function ShiftContextBadge({ state }) {
  if (!state) return null
  const items = []
  if (state.anomaly?.flag && state.anomaly.type === 'excess_idle') {
    items.push(`Idle flagged (${state.anomaly.current ?? '?'} min)`)
  }
  if (state.safety?.level && state.safety.level !== 'SAFE') {
    items.push(`Safety ${state.safety.level}`)
  }
  if (state.weather && state.weather !== 'clear') {
    items.push(`Weather: ${state.weather}`)
  }
  if (!items.length) return null

  return (
    <div className="mx-4 mb-2 flex flex-wrap gap-1.5">
      <span className="text-2xs text-ink3">Shift context shared with assistant:</span>
      {items.map((item) => (
        <span key={item} className="inline-flex items-center rounded-md border border-cat/25 bg-cat/8 px-1.5 py-0.5 text-2xs font-medium text-cat/80">
          {item}
        </span>
      ))}
    </div>
  )
}

// ── Main AIAssistant ─────────────────────────────────────────────────────────

export default function AIAssistant() {
  const { state } = useApp()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lastQ, setLastQ] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (question) => {
    const q = (question ?? input).trim()
    if (!q || loading) return

    setInput('')
    setLastQ(q)
    setMessages((prev) => [...prev, { type: 'user', text: q }])
    setLoading(true)

    try {
      const data = await api.post('/training/assistant', { question: q })
      setMessages((prev) => [...prev, { type: 'assistant', ...data }])
    } catch (err) {
      setMessages((prev) => [...prev, { type: 'error', error: err.message }])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const retry = () => {
    // Remove the last error message and retry
    setMessages((prev) => prev.filter((m, i) => !(i === prev.length - 1 && m.type === 'error')))
    send(lastQ)
  }

  const clear = () => {
    setMessages([])
    setLastQ('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* ── Header card ──────────────────────────────────────────────────── */}
      <Card>
        <div className="flex items-start justify-between gap-4 px-5 py-4">
          <div>
            <CardHeader
              icon={Bot}
              title="AI Training Assistant"
              subtitle="Ask about operation, safety, troubleshooting, and productivity"
            />
          </div>
          {messages.length > 0 && (
            <button className="btn btn-ghost btn-sm shrink-0" onClick={clear}>
              New conversation
            </button>
          )}
        </div>

        {/* Disclaimer */}
        <div className="mx-5 mb-4 flex items-start gap-2 rounded-xl border border-line bg-raised px-3 py-2.5">
          <Database size={13} className="mt-0.5 shrink-0 text-ink3" />
          <p className="text-2xs text-ink3 leading-relaxed">
            Answers are grounded in the operator training knowledge base.
            For safety-critical decisions, always consult your site supervisor and follow
            site-specific procedures. This assistant supplements — it does not replace —
            deterministic safety systems.
          </p>
        </div>
      </Card>

      {/* ── Chat area ────────────────────────────────────────────────────── */}
      <Card className="flex flex-col min-h-[520px]">
        {/* Message thread */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <WelcomeState onAsk={(q) => send(q)} />
          ) : (
            messages.map((msg, i) => {
              if (msg.type === 'user') return <UserBubble key={i} text={msg.text} />
              if (msg.type === 'assistant') return <AssistantBubble key={i} message={msg} />
              if (msg.type === 'error') return <ErrorBubble key={i} error={msg.error} onRetry={i === messages.length - 1 ? retry : null} />
              return null
            })
          )}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-end gap-2">
                <div className="shrink-0 grid h-8 w-8 place-items-center rounded-xl bg-anom/15 border border-anom/30">
                  <Bot size={14} className="text-anom" />
                </div>
                <div className="rounded-2xl rounded-bl-sm border border-line bg-panel2 px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-ink3">
                    <Loader2 size={14} className="animate-spin" />
                    Searching knowledge base…
                  </div>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Shift context */}
        {state?.shift?.active && <ShiftContextBadge state={state} />}

        {/* Suggested chips (shown when chat has messages) */}
        {messages.length > 0 && !loading && (
          <div className="px-4 pb-2 flex flex-wrap gap-1.5 border-t border-line pt-3">
            <span className="text-2xs text-ink3 w-full mb-1">Suggested follow-ups:</span>
            {SUGGESTED.slice(0, 4).map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="rounded-lg border border-line bg-panel2 px-2.5 py-1 text-2xs text-ink2 hover:border-line2 hover:text-ink transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-line p-3">
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about machine operation, safety, or troubleshooting…"
                rows={1}
                className="w-full resize-none rounded-xl border border-line bg-panel2 px-4 py-3 text-sm text-ink placeholder:text-ink3 focus:border-cat/40 focus:outline-none focus:ring-0 transition-colors"
                style={{ minHeight: 48, maxHeight: 160 }}
                onInput={(e) => {
                  e.target.style.height = 'auto'
                  e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
                }}
                disabled={loading}
              />
            </div>
            <button
              className="btn btn-primary btn-md shrink-0 self-end"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              aria-label="Send message"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
          <p className="mt-1.5 text-2xs text-ink3 px-1">
            Press <kbd className="rounded border border-line px-1 py-0.5 font-mono text-2xs">Enter</kbd> to send ·{' '}
            <kbd className="rounded border border-line px-1 py-0.5 font-mono text-2xs">Shift+Enter</kbd> for new line
          </p>
        </div>
      </Card>
    </div>
  )
}
