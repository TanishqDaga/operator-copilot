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
