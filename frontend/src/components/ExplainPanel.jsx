import { Loader2, MessageSquareText, RefreshCw } from 'lucide-react'
import { useApp } from '../lib/store'
import { Card, CardHeader, Chip, Source } from './ui'

const FACT_LABEL = {
  risk: 'Risk level', reasons: 'Reasons', distance_m: 'Distance (m)', ttc_s: 'Time to contact (s)', speed_kmh: 'Speed (km/h)',
  weather: 'Weather', anomaly: 'Anomaly', idle_min: 'Idle (min)', baseline_idle_min: 'Your usual idle (min)',
  anomaly_current: 'Current', anomaly_baseline: 'Your usual', anomaly_unit: 'Unit', eta_change_min: 'ETA change (min)',
  eta_change_reason: 'ETA change reason',
}

export default function ExplainPanel({ compact = false }) {
  const { explanation, explaining, explain, active, meta } = useApp()
  const facts = explanation?.context ? Object.entries(explanation.context).filter(([k]) => k !== 'limits') : []

  return (
    <Card>
      <CardHeader
        icon={MessageSquareText}
        title="Explanation"
        subtitle="Explains the rule engine's decision — never sets severity"
        right={
          <button className="btn btn-ghost btn-sm" onClick={() => explain()} disabled={!active || explaining}>
            {explaining ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />}
            Explain now
          </button>
        }
      />
      <div className="px-5 pb-5">
        {explanation ? (
          <div key={explanation.at} className="animate-rise">
            <p className={`${compact ? 'text-base' : 'text-lg'} leading-relaxed text-ink font-medium`}>{explanation.text}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Chip tone={explanation.source === 'llm' ? 'info' : 'default'}>
                {explanation.source === 'llm' ? `LLM · ${explanation.model}` : 'Template (no model call)'}
              </Chip>
              <span className="text-2xs text-ink3 num">{explanation.at}</span>
              {explanation.note && <span className="text-2xs text-ink3">· {explanation.note}</span>}
            </div>
            {!compact && facts.length > 0 && (
              <div className="mt-4 rounded-xl border border-line bg-panel2 p-3">
                <div className="label mb-2">Facts given to the explainer</div>
                <dl className="grid grid-cols-1 gap-x-6 gap-y-1 sm:grid-cols-2">
                  {facts.map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-3 text-[13px]">
                      <dt className="text-ink3">{FACT_LABEL[k] || k}</dt>
                      <dd className="num text-ink2 text-right truncate">{Array.isArray(v) ? v.join(', ') || '—' : String(v)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-ink3">
            {active ? 'Generated automatically when the rule engine goes CRITICAL, or on demand.' : 'Available once the shift has started.'}
          </p>
        )}
        <Source className="mt-4">
          {meta?.llm?.available
            ? `LLM (${meta.llm.model}, ${meta.llm.timeout_s}s timeout) with instant template fallback on any failure or if it cites a number not in the facts.`
            : 'No LLM key configured — explanations come from the deterministic template, built only from the facts above.'}
        </Source>
      </div>
    </Card>
  )
}
