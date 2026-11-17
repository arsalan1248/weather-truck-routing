import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { riskColor } from '../lib/risk'
import type { RouteOption } from '../lib/types'

interface Props {
  route: RouteOption
  selected: boolean
  onSelect: () => void
}

export function RouteCard({ route, selected, onSelect }: Props) {
  const { summary } = route
  const unsafe = summary.no_travel_miles > 0

  return (
    <button type="button" className={`route-card${selected ? ' selected' : ''}`} onClick={onSelect}>
      <div className="route-card-header">
        <strong>{route.name}</strong>
        {route.is_recommended && <span className="badge recommended">Recommended</span>}
        {unsafe && <span className="badge unsafe">Unsafe</span>}
      </div>

      <div className="route-stats">
        <span>{formatMiles(route.distance_miles)}</span>
        <span>{formatDuration(route.duration_minutes)}</span>
        <span>Arrives {formatDateTime(route.arrival_time)}</span>
      </div>

      {/* One coloured block per checkpoint, start to finish */}
      <div className="risk-strip" aria-hidden="true">
        {route.checkpoints.map((checkpoint) => (
          <span key={checkpoint.mile} style={{ background: riskColor(checkpoint.risk_level) }} />
        ))}
      </div>

      <dl className="risk-totals">
        <div>
          <dt>Severe</dt>
          <dd>{formatMiles(summary.severe_miles)}</dd>
        </div>
        <div>
          <dt>High</dt>
          <dd>{formatMiles(summary.high_miles)}</dd>
        </div>
        <div>
          <dt>Avg risk</dt>
          <dd>{summary.average_risk.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Worst</dt>
          <dd>{summary.worst_risk}</dd>
        </div>
      </dl>
      {unsafe && <p className="unsafe-note">{formatMiles(summary.no_travel_miles)} in No Travel conditions</p>}
    </button>
  )
}
