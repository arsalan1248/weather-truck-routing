import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'

// MapLibre builds its worker URL at runtime, which bundlers can't follow, so the
// worker file never makes it into the build. Importing it here lets Vite bundle
// it, and MapLibre is told where it ended up.
setWorkerUrl(workerUrl)
