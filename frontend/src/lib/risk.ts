import type { ExpressionSpecification } from 'maplibre-gl'
import type { RiskLabel } from './types'

export const RISK_LEVELS: { label: RiskLabel; color: string }[] = [
  { label: 'Low', color: '#16a34a' },
  { label: 'Moderate', color: '#eab308' },
  { label: 'High', color: '#f97316' },
  { label: 'Severe', color: '#dc2626' },
  { label: 'No Travel', color: '#7e22ce' },
]

export function riskColor(level: number): string {
  return RISK_LEVELS[Math.min(Math.max(Math.floor(level), 0), RISK_LEVELS.length - 1)].color
}

// MapLibre colour ramp: a score of 2.5 sits between High and Severe.
export function riskColorRamp(score: ExpressionSpecification): ExpressionSpecification {
  const stops = RISK_LEVELS.flatMap(({ color }, level) => [level, color])
  return ['interpolate', ['linear'], score, ...stops] as ExpressionSpecification
}
