export type RiskLabel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel'

export type CheckpointInterval = 10 | 25 | 50

export interface Place {
  name: string
  lat: number
  lon: number
}

export interface TripRequest {
  origin: Place
  destination: Place
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_miles: CheckpointInterval
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  wind_mph: number
  rain_in_per_hr: number
  snow_in_per_hr: number
  risk: RiskLabel
  risk_level: number
  reasons: string[]
}

export interface RouteOption {
  id: string
  name: string
  rank: number
  is_recommended: boolean
  distance_miles: number
  duration_minutes: number
  arrival_time: string
  summary: {
    severe_miles: number
    high_miles: number
    no_travel_miles: number
    average_risk: number
    worst_risk: RiskLabel
  }
  geometry: [number, number][] // [lon, lat]
  checkpoints: Checkpoint[]
}

export interface Trip {
  origin: string
  destination: string
  departure_time: string
  load_weight_lb: number
  checkpoint_interval_miles: CheckpointInterval
  recommended_route_id: string
  recommendation_reason: string
  routes: RouteOption[]
  heatmap: Heatmap
}

export interface Heatmap {
  start_time: string
  hours: number
  spacing_miles: number
  points: [number, number][] // [lon, lat]
  scores: number[][] // scores[hour][point], 0-4
}
