import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  // MapLibre's worker is an ES module (see src/lib/maplibreWorker.ts).
  worker: {
    format: 'es',
  },
  build: {
    // MapLibre alone is over 1 MB minified (about 300 KB gzipped).
    chunkSizeWarningLimit: 1500,
  },
})
