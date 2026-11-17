import { useEffect, useState } from 'react'
import { formatDateTime } from '../lib/format'
import type { Heatmap } from '../lib/types'

const PLAY_STEP_MS = 600

interface Props {
  heatmap: Heatmap
  hour: number
  onHourChange: (hour: number) => void
  showHeatmap: boolean
  onToggleHeatmap: (show: boolean) => void
}

export function ForecastSlider({ heatmap, hour, onHourChange, showHeatmap, onToggleHeatmap }: Props) {
  const [playing, setPlaying] = useState(false)
  const maxHour = heatmap.hours

  useEffect(() => {
    if (!playing) return
    const timer = window.setInterval(() => {
      onHourChange(hour >= maxHour ? 0 : hour + 1)
    }, PLAY_STEP_MS)
    return () => window.clearInterval(timer)
  }, [playing, hour, maxHour, onHourChange])

  const time = new Date(Date.parse(heatmap.start_time) + hour * 3_600_000)

  return (
    <div className="forecast-panel">
      <div className="forecast-header">
        <label className="toggle">
          <input type="checkbox" checked={showHeatmap} onChange={(event) => onToggleHeatmap(event.target.checked)} />
          Weather heatmap
        </label>
        <span className="forecast-time">
          {formatDateTime(time)} <span className="muted">(+{hour} h)</span>
        </span>
      </div>
      <div className="forecast-controls">
        <button
          type="button"
          className="play-button"
          onClick={() => setPlaying((p) => !p)}
          aria-label={playing ? 'Pause' : 'Play forecast'}
        >
          {playing ? '❚❚' : '▶'}
        </button>
        <input
          type="range"
          min={0}
          max={maxHour}
          value={hour}
          aria-label="Forecast hour"
          onChange={(event) => {
            setPlaying(false)
            onHourChange(Number(event.target.value))
          }}
        />
      </div>
    </div>
  )
}
