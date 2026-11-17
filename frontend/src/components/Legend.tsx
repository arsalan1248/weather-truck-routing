import { RISK_LEVELS } from '../lib/risk'

export function Legend() {
  return (
    <div className="legend">
      {RISK_LEVELS.map(({ label, color }) => (
        <span key={label}>
          <i style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  )
}
