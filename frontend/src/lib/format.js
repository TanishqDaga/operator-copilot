export const LEVEL = {
  SAFE: { text: 'text-safe', bg: 'bg-safe', soft: 'bg-safe-bg', border: 'border-safe/40', ring: 'ring-safe/30', label: 'Safe' },
  WARNING: { text: 'text-warn', bg: 'bg-warn', soft: 'bg-warn-bg', border: 'border-warn/50', ring: 'ring-warn/30', label: 'Warning' },
  CRITICAL: { text: 'text-crit', bg: 'bg-crit', soft: 'bg-crit-bg', border: 'border-crit/60', ring: 'ring-crit/40', label: 'Critical' },
  ANOMALY: { text: 'text-anom', bg: 'bg-anom', soft: 'bg-anom-bg', border: 'border-anom/40', ring: 'ring-anom/30', label: 'Anomaly' },
  INFO: { text: 'text-info', bg: 'bg-info', soft: 'bg-info-bg', border: 'border-info/30', ring: 'ring-info/30', label: 'Info' },
}

export const REASON_LABEL = {
  person_close: 'Person close',
  ttc_low: 'Low time-to-contact',
  seatbelt: 'Seatbelt unfastened',
  wet_ground: 'Wet ground speed',
}

export const ANOMALY_LABEL = {
  excess_idle: 'Excess idle',
  slow_cycle: 'Slow cycle',
  hyd_overheat: 'Hydraulic temp high',
  hyd_cold: 'Hydraulic temp low',
  high_fuel_burn: 'High fuel burn',
  rpm_abnormal: 'Engine speed unusual',
  payload_abnormal: 'Payload unusual',
}

export const PHASE_LABEL = {
  dig: 'Digging', swing_loaded: 'Swing (loaded)', dump: 'Dumping', swing_return: 'Swing (return)',
  position: 'Positioning', tram: 'Tramming', idle: 'Idle',
}

export const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—' : Number(v).toFixed(d))
export const signed = (v) => (v > 0 ? `+${v}` : `${v}`)
export const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`

// ---- weather-aware planner ----
export const CONDITION = {
  clear: { label: 'Clear', tone: 'text-safe' },
  cloudy: { label: 'Cloudy', tone: 'text-ink2' },
  rain: { label: 'Rain', tone: 'text-info' },
  wind: { label: 'Wind', tone: 'text-warn' },
  low_visibility: { label: 'Low vis.', tone: 'text-anom' },
}

export const SENS_TONE = { low: 'safe', medium: 'warn', high: 'crit' }
export const FACTOR_LABEL = { rain: 'Rain', wind: 'Wind', visibility: 'Visibility' }
export const DURATION_SOURCE = { manager_estimate: 'manager estimate', eta_model: 'ETA model' }

export const PLAN_STATUS = {
  draft: { label: 'Draft', tone: 'default' },
  recommended: { label: 'Recommendation ready', tone: 'info' },
  overridden: { label: 'Recommendation + overrides', tone: 'cat' },
  accepted: { label: 'Recommendation accepted', tone: 'safe' },
  published: { label: 'Published', tone: 'safe' },
}

/** Visual tone for a planner recommendation label. */
export function moveTone(rec) {
  if (!rec) return 'default'
  if (rec.source === 'manager_override') return 'cat'
  if (rec.source === 'locked') return 'default'
  if (rec.label?.endsWith('sensitive')) return 'info'
  if (rec.label?.endsWith('tolerant')) return 'safe'
  return 'default'
}

export const toMin = (hhmm) => {
  const [h, m] = String(hhmm).split(':').map(Number)
  return h * 60 + m
}

// ---- operator task planner ----
export const hm = (min) => {
  if (min == null) return '—'
  if (min < 1) return '<1 min'
  if (min < 60) return `${Math.round(min)} min`
  return `${Math.floor(min / 60)}h ${String(Math.round(min % 60)).padStart(2, '0')}m`
}

export const GUIDANCE_TONE = {
  SAFETY_CRITICAL: 'crit', SAFETY_WARNING: 'warn', OPERATIONAL_ISSUE: 'anom', CURRENT_TASK: 'cat', WEATHER: 'info', PRODUCTIVITY: 'safe',
}
export const GUIDANCE_LABEL = {
  SAFETY_CRITICAL: 'Critical safety', SAFETY_WARNING: 'Safety warning', OPERATIONAL_ISSUE: 'Machine issue',
  CURRENT_TASK: 'Current task', WEATHER: 'Weather', PRODUCTIVITY: 'Productivity',
}
