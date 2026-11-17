import type { Heatmap, Place, Trip, TripRequest } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function planTrip(request: TripRequest): Promise<Trip> {
  return send<Trip>(`${API_URL}/api/trips/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export async function fetchHeatmap(tripId: string): Promise<Heatmap> {
  return send<Heatmap>(`${API_URL}/api/trips/${tripId}/heatmap/`)
}

export async function pingServer(): Promise<void> {
  await send(`${API_URL}/api/health/`)
}

interface PhotonFeature {
  geometry: { coordinates: [number, number] }
  properties: { name?: string; city?: string; state?: string; country?: string }
}

export async function searchPlaces(query: string, signal: AbortSignal): Promise<Place[]> {
  const params = new URLSearchParams({ q: query, limit: '6', lang: 'en' })
  const data = await send<{ features: PhotonFeature[] }>(`https://photon.komoot.io/api/?${params}`, { signal })

  return data.features.map(({ geometry, properties }) => {
    const parts = [properties.name, properties.city, properties.state, properties.country]
    const name = [...new Set(parts.filter(Boolean))].join(', ')
    const [lon, lat] = geometry.coordinates
    return { name, lat, lon }
  })
}

async function send<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error("Can't reach the server. Check your connection and try again.")
  }

  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(errorMessage(body) ?? `Request failed (${response.status}).`)
  return body as T
}

// DRF errors look like {"detail": "..."} or {"field": ["..."], "origin": {"lat": ["..."]}}.
function errorMessage(body: unknown): string | undefined {
  if (!body || typeof body !== 'object') return undefined
  if ('detail' in body && typeof body.detail === 'string') return body.detail

  const first = Object.values(body)[0]
  if (Array.isArray(first)) return String(first[0])
  return errorMessage(first)
}
