# Weather-Aware Truck Routing

A React + Django app that helps a truck driver pick the safest route. It compares three routes using the weather forecast **at the time the truck will reach each point**, the load weight and the travel time.

- **Live app:** _added after deployment_
- **API:** _added after deployment_

## What it does

1. Enter an origin, destination, departure time, load weight and how often to check the weather (every 10, 25 or 50 miles).
2. The backend finds three route options and places checkpoints along each one.
3. For each checkpoint it works out when the truck arrives and looks up the forecast for that place and hour.
4. Each checkpoint gets a risk level from the brief's wind, rain and snow table, with the load rules applied to wind.
5. The routes are ranked and one is recommended, with a one-line reason.
6. The map shows all routes, colour-coded checkpoints (click one for its ETA and weather), and a weather risk heatmap around the trip with a 0–48 hour slider. A truck marker shows where the selected route would be at the chosen hour.

## How it works

### Routes

Routes come from the public [OSRM](https://project-osrm.org/) server. OSRM often returns only one or two alternatives, so the rest come from routing through a point to the left or right of the straight line between origin and destination. A detour is only kept if it's less than 1.5× the main route's length and doesn't mostly overlap a route we already have. The first detours are requested at the same time as the main route, so a plan usually takes about two seconds.

OSRM's travel times are for cars, so each stretch of road is capped at **65 mph** to give realistic truck arrival times.

### Weather

Forecasts come from [Open-Meteo](https://open-meteo.com/): hourly wind speed (mph), rain (in) and snowfall (in). Open-Meteo accepts many locations per request, so all checkpoints on all three routes are fetched in one batched call. Hourly rain and snow totals are read as in/hr.

### Risk rules

`backend/trips/services/risk.py` follows the brief's table line by line:

| | Low | Moderate | High | Severe | No Travel |
|---|---|---|---|---|---|
| Wind (mph) | < 25 | 25–34 | 35–44 | 45–54 | ≥ 55 |
| Rain (in/hr) | < 0.10 | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 |
| Snow (in/hr) | < 0.5 | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | > 3.0 |

Load rules, applied to the wind level: 45–54 mph with more than 30,000 lb becomes No Travel, and 35–44 mph with more than 40,000 lb becomes Severe. A checkpoint's risk is the worst of wind, rain and snow.

### Recommendation

Each checkpoint stands for the miles halfway to its neighbours, which gives every route its Severe miles, High miles and a mile-weighted average risk (Low = 0 … No Travel = 4). Routes are ranked by:

1. Fewest Severe miles
2. Fewest High miles
3. Lowest average risk
4. Shortest travel time

### Heatmap

The heatmap covers a 60-mile corridor around all three routes on a regular grid of up to 250 points, with the spacing chosen to fit. It loads in a second request, so the routes appear without waiting for it. All 49 hours (0 to 48 after departure) arrive in one response of about 70 KB.

Each grid point stores all 49 hourly scores as properties (`s0` … `s48`). Moving the slider only changes which property the map's style reads, so no data is re-sent and nothing is rebuilt. That's what keeps the slider and the play button smooth.

The score is a smooth 0–4 version of the risk level, so the colours blend between grid points. Its whole-number part always matches the checkpoint risk level, e.g. 2.6 is High. It's drawn as blurred circles rather than MapLibre's built-in heatmap layer, because that layer sums up overlapping points (density), while here each point is a value.

### Caching

Plans and forecasts are cached in SQLite (Django's database cache), so every server worker sees the same data. The heatmap request looks the trip up by its ID, and repeated forecasts are served from the cache for 30 minutes.

## Assumptions

- **Checkpoint spacing:** the user picks 10, 25 or 50 miles. There's always a checkpoint at the destination too.
- **Boundaries:** where the table puts a value on two rows (e.g. rain of exactly 0.25 in/hr), it gets the higher level. Values marked `>` in the table are strict, so 1.00 in/hr of rain is Severe and 1.01 is No Travel.
- **Wind:** sustained wind speed, not gusts.
- **No Travel:** the brief's ranking doesn't mention it, so any route with No Travel miles is ranked last and marked unsafe. If every route has it, the app says so and suggests a different departure time.
- **Truck speed:** car travel times, capped at 65 mph.
- **Departure:** within the next 7 days, so the forecast covers the whole trip plus the 48-hour heatmap.
- **Heatmap hours** count from the departure hour.

## Running locally

Needs Python 3.12+ and Node 20+. No API keys are required.

**Backend** (http://localhost:8000):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py createcachetable
python manage.py runserver
```

**Frontend** (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

The frontend calls `http://localhost:8000` by default. Set `VITE_API_URL` to point it somewhere else (see `frontend/.env.example`).

## Tests

```bash
cd backend && python manage.py test     # risk rules, ranking, checkpoints, API (external calls mocked)
cd frontend && npm test                 # truck position and formatting helpers
```

The backend tests check every boundary in the risk table, the load rules at exactly 30,000 and 40,000 lb, and each ranking tie-breaker.

## API

`POST /api/trips/`

```json
{
  "origin": { "name": "Dallas, TX", "lat": 32.7767, "lon": -96.797 },
  "destination": { "name": "Denver, CO", "lat": 39.7392, "lon": -104.9903 },
  "departure_time": "2026-11-18T14:00:00Z",
  "load_weight_lb": 42000,
  "checkpoint_interval_miles": 25
}
```

The response has `trip_id`, `recommended_route_id`, `recommendation_reason`, and `routes`. Each route has its geometry, summary and checkpoints, and each checkpoint has its ETA, weather, risk and reasons.

`GET /api/trips/<trip_id>/heatmap/` returns `points`, `spacing_miles`, `start_time` and `scores[hour][point]` for hours 0–48.

`GET /api/health/` is used by the frontend to wake the server on free hosting.

## Deployment

- **Backend:** Render free web service, defined in `render.yaml`. Free services sleep after 15 minutes idle, so the first request can take up to a minute. The frontend pings the server on load and shows a notice while it wakes.
- **Frontend:** Vercel, with the root directory set to `frontend` and `VITE_API_URL` set to the Render URL.

## Project layout

```
backend/
  config/                 settings and URLs
  trips/
    services/
      routing.py          OSRM routes and detour alternatives
      weather.py          batched Open-Meteo forecasts
      risk.py             the risk table and load rules
      planner.py          checkpoints, ETAs, per-route risk totals
      recommendation.py   ranking and the explanation
      heatmap.py          corridor grid and 0-48 h scores
    serializers.py        request validation
    views.py              API endpoints
    tests/
frontend/
  src/
    components/           form, route cards, map, forecast slider, legend
    lib/                  API client, types, risk colours, formatting, truck position
```

## With more time

- Show wind gusts alongside sustained wind, and let the user choose which one drives the risk.
- Use a truck-specific routing profile (height, weight and hazmat restrictions) instead of capping car times.
- Suggest the safest departure time within the 48-hour window.
- Move the cache to Redis if the app runs on more than one server.
