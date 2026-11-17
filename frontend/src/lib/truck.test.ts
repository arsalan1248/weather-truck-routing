import { describe, expect, it } from 'vitest'
import { truckPositionAt } from './truck'
import type { Checkpoint, RouteOption } from './types'

function checkpoint(lon: number, lat: number, eta: string): Checkpoint {
  return {
    mile: 0, lat, lon, eta,
    wind_mph: 0, rain_in_per_hr: 0, snow_in_per_hr: 0,
    risk: 'Low', risk_level: 0, reasons: [],
  }
}

const route = {
  checkpoints: [
    checkpoint(-97, 30, '2026-11-20T06:00:00Z'),
    checkpoint(-97, 31, '2026-11-20T07:00:00Z'),
    checkpoint(-97, 33, '2026-11-20T08:00:00Z'),
  ],
} as RouteOption

describe('truckPositionAt', () => {
  it('stays at the start before departure', () => {
    expect(truckPositionAt(route, new Date('2026-11-20T05:00:00Z'))).toEqual([-97, 30])
  })

  it('moves between checkpoints in proportion to the time', () => {
    const [lon, lat] = truckPositionAt(route, new Date('2026-11-20T07:30:00Z'))
    expect(lon).toBe(-97)
    expect(lat).toBeCloseTo(32)
  })

  it('stays at the destination after arrival', () => {
    expect(truckPositionAt(route, new Date('2026-11-21T00:00:00Z'))).toEqual([-97, 33])
  })
})
