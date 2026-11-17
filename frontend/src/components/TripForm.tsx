import { useState, type FormEvent } from 'react'
import { nextFullHour, toLocalInputValue } from '../lib/format'
import type { CheckpointInterval, Place, TripRequest } from '../lib/types'
import { PlaceSearch } from './PlaceSearch'

const INTERVALS: CheckpointInterval[] = [10, 25, 50]

interface Props {
  busy: boolean
  onSubmit: (request: TripRequest) => void
}

export function TripForm({ busy, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInputValue(nextFullHour()))
  const [load, setLoad] = useState('35000')
  const [checkpointInterval, setCheckpointInterval] = useState<CheckpointInterval>(25)
  const [error, setError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!origin || !destination) {
      setError('Pick the origin and destination from the suggestions.')
      return
    }
    setError(null)
    onSubmit({
      origin,
      destination,
      departure_time: new Date(departure).toISOString(),
      load_weight_lb: Number(load),
      checkpoint_interval_miles: checkpointInterval,
    })
  }

  return (
    <form className="trip-form" onSubmit={handleSubmit}>
      <PlaceSearch label="Origin" placeholder="e.g. Dallas, TX" value={origin} onChange={setOrigin} />
      <PlaceSearch label="Destination" placeholder="e.g. Denver, CO" value={destination} onChange={setDestination} />

      <div className="field-row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            required
            value={departure}
            onChange={(event) => setDeparture(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load (lb)</label>
          <input
            id="load"
            type="number"
            min={0}
            max={200000}
            step={500}
            required
            value={load}
            onChange={(event) => setLoad(event.target.value)}
          />
        </div>
      </div>

      <fieldset className="field">
        <legend>Check weather every</legend>
        <div className="segmented">
          {INTERVALS.map((miles) => (
            <button
              key={miles}
              type="button"
              className={miles === checkpointInterval ? 'active' : undefined}
              aria-pressed={miles === checkpointInterval}
              onClick={() => setCheckpointInterval(miles)}
            >
              {miles} mi
            </button>
          ))}
        </div>
      </fieldset>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? 'Checking routes and weather…' : 'Find the safest route'}
      </button>
    </form>
  )
}
