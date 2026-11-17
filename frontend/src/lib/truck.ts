import type { RouteOption } from './types'

/** Where the truck is at `time`, interpolated between checkpoint arrival times. Returns [lon, lat]. */
export function truckPositionAt(route: RouteOption, time: Date): [number, number] {
  const t = time.getTime()
  const checkpoints = route.checkpoints
  const first = checkpoints[0]
  const last = checkpoints[checkpoints.length - 1]

  if (t <= Date.parse(first.eta)) return [first.lon, first.lat]
  if (t >= Date.parse(last.eta)) return [last.lon, last.lat]

  const nextIndex = checkpoints.findIndex((checkpoint) => Date.parse(checkpoint.eta) > t)
  const before = checkpoints[nextIndex - 1]
  const after = checkpoints[nextIndex]
  const start = Date.parse(before.eta)
  const fraction = (t - start) / (Date.parse(after.eta) - start)
  return [before.lon + (after.lon - before.lon) * fraction, before.lat + (after.lat - before.lat) * fraction]
}
