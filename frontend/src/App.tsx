import { useCallback, useEffect, useMemo, useState } from 'react'
import { ForecastSlider } from './components/ForecastSlider'
import { Legend } from './components/Legend'
import { RouteCard } from './components/RouteCard'
import { TripForm } from './components/TripForm'
import { TripMap } from './components/TripMap'
import { fetchHeatmap, pingServer, planTrip } from './lib/api'
import { truckPositionAt } from './lib/truck'
import type { Heatmap, Trip, TripRequest } from './lib/types'

export default function App() {
  const serverWaking = useServerWakeUp()
  const [trip, setTrip] = useState<Trip | null>(null)
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState<string | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)

  const [heatmap, setHeatmap] = useState<Heatmap | null>(null)
  const [heatmapLoading, setHeatmapLoading] = useState(false)
  const [heatmapError, setHeatmapError] = useState<string | null>(null)
  const [showHeatmap, setShowHeatmap] = useState(true)
  const [hour, setHour] = useState(0)

  async function handlePlan(request: TripRequest) {
    setPlanning(true)
    setPlanError(null)
    setHeatmap(null)
    setHeatmapError(null)
    try {
      const newTrip = await planTrip(request)
      setTrip(newTrip)
      setSelectedRouteId(newTrip.recommended_route_id)
      setHour(0)
      loadHeatmap(newTrip.trip_id)
    } catch (error) {
      setPlanError((error as Error).message)
    } finally {
      setPlanning(false)
    }
  }

  // Loaded after the routes so they appear without waiting for the bigger forecast grid.
  async function loadHeatmap(tripId: string) {
    setHeatmapLoading(true)
    try {
      setHeatmap(await fetchHeatmap(tripId))
    } catch (error) {
      setHeatmapError((error as Error).message)
    } finally {
      setHeatmapLoading(false)
    }
  }

  const handleHourChange = useCallback((value: number) => setHour(value), [])

  const selectedRoute = trip?.routes.find((route) => route.id === selectedRouteId) ?? null
  const truckPosition = useMemo(() => {
    if (!selectedRoute || !heatmap) return null
    return truckPositionAt(selectedRoute, new Date(Date.parse(heatmap.start_time) + hour * 3_600_000))
  }, [selectedRoute, heatmap, hour])

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>Weather-Aware Truck Routing</h1>
          <p className="muted">Compare routes by the weather the truck will actually drive through.</p>
        </header>

        {serverWaking && (
          <p className="notice">Waking up the server. On free hosting this can take up to a minute the first time.</p>
        )}

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
          heatmap={heatmap}
          hour={hour}
          showHeatmap={showHeatmap}
          truckPosition={truckPosition}
        />
        <Legend />
        {trip && (
          <ForecastSlider
            heatmap={heatmap}
            loading={heatmapLoading}
            error={heatmapError}
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

/** True while the backend is slow to answer its first request, i.e. a free server waking from sleep. */
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
