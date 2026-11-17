import type { Feature, FeatureCollection, LineString, Point } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef, useState } from 'react'
import Map, { Layer, Marker, NavigationControl, Popup, Source, type MapLayerMouseEvent, type MapRef } from 'react-map-gl/maplibre'
import { formatDateTime } from '../lib/format'
import '../lib/maplibreWorker'
import { riskColor, riskColorRamp } from '../lib/risk'
import type { Checkpoint, Heatmap, RouteOption, Trip } from '../lib/types'

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'
const INTERACTIVE_LAYERS = ['checkpoints', 'routes']

interface Props {
  trip: Trip | null
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  heatmap: Heatmap | null
  hour: number
  showHeatmap: boolean
  truckPosition: [number, number] | null
}

interface OpenPopup {
  tripId: string
  route: RouteOption
  checkpoint: Checkpoint
}

export function TripMap({ trip, selectedRouteId, onSelectRoute, heatmap, hour, showHeatmap, truckPosition }: Props) {
  const mapRef = useRef<MapRef>(null)
  const [popup, setPopup] = useState<OpenPopup | null>(null)
  const [hovering, setHovering] = useState(false)

  // A popup from a previous trip is simply not shown.
  const visiblePopup = popup && popup.tripId === trip?.trip_id ? popup : null

  useEffect(() => {
    if (!trip) return
    const coordinates = trip.routes.flatMap((route) => route.geometry)
    const lons = coordinates.map(([lon]) => lon)
    const lats = coordinates.map(([, lat]) => lat)
    mapRef.current?.fitBounds(
      [[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]],
      { padding: 60, duration: 800 },
    )
  }, [trip])

  const routeLines = useMemo(() => buildRouteLines(trip, selectedRouteId), [trip, selectedRouteId])
  const checkpoints = useMemo(() => buildCheckpoints(trip, selectedRouteId), [trip, selectedRouteId])
  const heatmapPoints = useMemo(() => buildHeatmapPoints(heatmap), [heatmap])
  const heatmapRadius = useMemo(() => radiusExpression(heatmap), [heatmap])

  // Every point already carries all 48 hours (s0...s48), so moving the slider only
  // changes which property the map reads. No data is re-sent to the GPU.
  const score: ExpressionSpecification = ['get', `s${hour}`]

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!feature || !trip) {
      setPopup(null)
      return
    }
    const route = trip.routes.find((r) => r.id === feature.properties.routeId)
    if (!route) return
    if (feature.layer.id === 'checkpoints') {
      setPopup({ tripId: trip.trip_id, route, checkpoint: route.checkpoints[feature.properties.index] })
    } else {
      onSelectRoute(route.id)
    }
  }

  return (
    <Map
      ref={mapRef}
      mapStyle={MAP_STYLE}
      initialViewState={{ longitude: -98.5, latitude: 39.5, zoom: 3.6 }}
      attributionControl={{ compact: true }}
      interactiveLayerIds={INTERACTIVE_LAYERS}
      cursor={hovering ? 'pointer' : 'grab'}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={handleClick}
    >
      <NavigationControl position="top-right" showCompass={false} />

      {heatmapPoints && (
        <Source id="heatmap" type="geojson" data={heatmapPoints}>
          <Layer
            id="heatmap"
            type="circle"
            layout={{ visibility: showHeatmap ? 'visible' : 'none' }}
            paint={{
              'circle-radius': heatmapRadius,
              'circle-color': riskColorRamp(score),
              // Calm areas stay see-through so the risky weather stands out.
              'circle-opacity': ['interpolate', ['linear'], score, 0, 0, 0.6, 0.1, 1, 0.35, 4, 0.55],
              'circle-blur': 1,
            }}
          />
        </Source>
      )}

      {routeLines && (
        <Source id="routes" type="geojson" data={routeLines}>
          <Layer
            id="routes-casing"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] }}
            paint={{ 'line-color': '#ffffff', 'line-width': ['case', ['get', 'selected'], 10, 6.5] }}
          />
          <Layer
            id="routes"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', ['get', 'selected'], 1, 0] }}
            paint={{
              'line-color': ['case', ['get', 'selected'], '#1d4ed8', '#64748b'],
              'line-width': ['case', ['get', 'selected'], 6, 3.5],
              'line-opacity': ['case', ['get', 'selected'], 1, 0.75],
            }}
          />
        </Source>
      )}

      {checkpoints && (
        <Source id="checkpoints" type="geojson" data={checkpoints}>
          <Layer
            id="checkpoints"
            type="circle"
            layout={{ 'circle-sort-key': ['case', ['get', 'selected'], 1, 0] }}
            paint={{
              'circle-radius': ['case', ['get', 'selected'], 6, 4],
              'circle-color': riskColorRamp(['get', 'level']),
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': ['case', ['get', 'selected'], 2, 1],
            }}
          />
        </Source>
      )}

      {trip?.routes.map((route) => {
        const [lon, lat] = route.geometry[Math.floor(route.geometry.length / 2)]
        return (
          <Marker key={route.id} longitude={lon} latitude={lat} onClick={() => onSelectRoute(route.id)}>
            <span className={`route-label${route.id === selectedRouteId ? ' selected' : ''}`}>{route.id}</span>
          </Marker>
        )
      })}

      {trip && (
        <>
          <Marker longitude={trip.routes[0].geometry[0][0]} latitude={trip.routes[0].geometry[0][1]}>
            <span className="endpoint start" title={trip.origin} />
          </Marker>
          <Marker longitude={trip.routes[0].geometry.at(-1)![0]} latitude={trip.routes[0].geometry.at(-1)![1]}>
            <span className="endpoint finish" title={trip.destination} />
          </Marker>
        </>
      )}

      {truckPosition && (
        <Marker longitude={truckPosition[0]} latitude={truckPosition[1]}>
          <span className="truck-marker" title="Truck position at the selected forecast hour">
            <TruckIcon />
          </span>
        </Marker>
      )}

      {visiblePopup && (
        <Popup
          longitude={visiblePopup.checkpoint.lon}
          latitude={visiblePopup.checkpoint.lat}
          onClose={() => setPopup(null)}
          closeOnClick={false}
          maxWidth="260px"
        >
          <CheckpointDetails route={visiblePopup.route} checkpoint={visiblePopup.checkpoint} />
        </Popup>
      )}
    </Map>
  )
}

function CheckpointDetails({ route, checkpoint }: { route: RouteOption; checkpoint: Checkpoint }) {
  return (
    <div className="checkpoint-popup">
      <div className="checkpoint-popup-title">
        <strong>{route.name}, mile {Math.round(checkpoint.mile)}</strong>
        <span className="risk-chip" style={{ background: riskColor(checkpoint.risk_level) }}>
          {checkpoint.risk}
        </span>
      </div>
      <p>Arrives {formatDateTime(checkpoint.eta)}</p>
      <ul>
        <li>Wind {checkpoint.wind_mph} mph</li>
        <li>Rain {checkpoint.rain_in_per_hr} in/hr</li>
        <li>Snow {checkpoint.snow_in_per_hr} in/hr</li>
      </ul>
      {checkpoint.reasons.length > 0 && (
        <p className="checkpoint-reasons">{checkpoint.reasons.join('. ')}</p>
      )}
    </div>
  )
}

function TruckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <path
        fill="currentColor"
        d="M3 5h11v9h1.5V8H19l3 4v4h-1.6a2.5 2.5 0 0 1-4.8 0H9.4a2.5 2.5 0 0 1-4.8 0H3V5Zm4 10a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm11 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2Zm-.5-5v2h3l-1.5-2h-1.5Z"
      />
    </svg>
  )
}

function buildRouteLines(trip: Trip | null, selectedRouteId: string | null): FeatureCollection<LineString> | null {
  if (!trip) return null
  return {
    type: 'FeatureCollection',
    features: trip.routes.map((route) => ({
      type: 'Feature',
      properties: { routeId: route.id, selected: route.id === selectedRouteId },
      geometry: { type: 'LineString', coordinates: route.geometry },
    })),
  }
}

function buildCheckpoints(trip: Trip | null, selectedRouteId: string | null): FeatureCollection<Point> | null {
  if (!trip) return null
  return {
    type: 'FeatureCollection',
    features: trip.routes.flatMap((route) =>
      route.checkpoints.map((checkpoint, index): Feature<Point> => ({
        type: 'Feature',
        properties: { routeId: route.id, index, level: checkpoint.risk_level, selected: route.id === selectedRouteId },
        geometry: { type: 'Point', coordinates: [checkpoint.lon, checkpoint.lat] },
      })),
    ),
  }
}

function buildHeatmapPoints(heatmap: Heatmap | null): FeatureCollection<Point> | null {
  if (!heatmap) return null
  return {
    type: 'FeatureCollection',
    features: heatmap.points.map((coordinates, i) => ({
      type: 'Feature',
      properties: Object.fromEntries(heatmap.scores.map((hourScores, hour) => [`s${hour}`, hourScores[i]])),
      geometry: { type: 'Point', coordinates },
    })),
  }
}

/** Circle size that keeps neighbouring grid points overlapping at every zoom level. */
function radiusExpression(heatmap: Heatmap | null): ExpressionSpecification {
  if (!heatmap) return ['literal', 0]
  const meanLat = heatmap.points.reduce((sum, [, lat]) => sum + lat, 0) / heatmap.points.length
  const kmPerPixelAtZoom0 = (40075 * Math.cos((meanLat * Math.PI) / 180)) / 512
  const radiusAtZoom0 = (heatmap.spacing_miles * 1.609 * 1.5) / kmPerPixelAtZoom0
  // Pixel size doubles with every zoom level.
  return ['interpolate', ['exponential', 2], ['zoom'], 0, radiusAtZoom0, 12, radiusAtZoom0 * 4096]
}
