import { useCallback, useEffect, useMemo, useState } from 'react'
import { ForecastSlider } from './components/ForecastSlider'
import { Legend } from './components/Legend'
import { RouteCard } from './components/RouteCard'
import { TripForm } from './components/TripForm'
import { TripMap } from './components/TripMap'
import { pingServer, planTrip } from './lib/api'
import { truckPositionAt } from './lib/truck'
import type { Trip, TripRequest } from './lib/types'

export default function App() {
  const serverWaking = useServerWakeUp()
  const [trip, setTrip] = useState<Trip | null>(null)
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [hour, setHour] = useState(0)

  async function handlePlan(request: TripRequest) {
    setPlanning(true)
    setPlanError(null)
    try {
      const newTrip = await planTrip(request)
      setTrip(newTrip)
      setSelectedRouteId(newTrip.recommended_route_id)
      setHour(0)
    } catch (error) {
      setPlanError((error as Error).message)
    } finally {
      setPlanning(false)
    }
  }

  const handleHourChange = useCallback((value: number) => setHour(value), [])

  const selectedRoute = trip?.routes.find((route) => route.id === selectedRouteId) ?? null
  const truckPosition = useMemo(() => {
    if (!trip || !selectedRoute) return null
    return truckPositionAt(selectedRoute, new Date(Date.parse(trip.heatmap.start_time) + hour * 3_600_000))
  }, [trip, selectedRoute, hour])

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>Weather-Aware Truck Routing</h1>
          <p className="muted">Compare routes by the weather the truck will actually drive through.</p>
        </header>

        {serverWaking && <p className="notice">Connecting to the server…</p>}

        <TripForm busy={planning} onSubmit={handlePlan} />
        {planError && <p className="form-error">{planError}</p>}

        {trip && (
          <section className="results" aria-live="polite">
            <div className="recommendation">
              <strong>Take Route {trip.recommended_route_id}.</strong> {trip.recommendation_reason}
            </div>
            {trip.routes.map((route) => (
              <RouteCard
                key={route.id}
                route={route}
                selected={route.id === selectedRouteId}
                onSelect={() => setSelectedRouteId(route.id)}
              />
            ))}
          </section>
        )}
      </aside>

      <main className="map-area">
        <TripMap
          trip={trip}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          hour={hour}
          showHeatmap={showHeatmap}
          truckPosition={truckPosition}
        />
        <Legend />
        {trip && (
          <ForecastSlider
            heatmap={trip.heatmap}
            hour={hour}
            onHourChange={handleHourChange}
            showHeatmap={showHeatmap}
            onToggleHeatmap={setShowHeatmap}
          />
        )}
      </main>
    </div>
  )
}

/** True while the backend is slow to answer its first request, e.g. a serverless function starting cold. */
function useServerWakeUp() {
  const [waking, setWaking] = useState(false)

  useEffect(() => {
    const timer = window.setTimeout(() => setWaking(true), 2000)
    pingServer()
      .catch(() => undefined)
      .finally(() => {
        window.clearTimeout(timer)
        setWaking(false)
      })
    return () => window.clearTimeout(timer)
  }, [])

  return waking
}
