import { describe, expect, it } from 'vitest'
import { formatDuration, toLocalInputValue } from './format'
import { RISK_LEVELS, riskColor } from './risk'

describe('formatDuration', () => {
  it('shows hours and padded minutes', () => {
    expect(formatDuration(910)).toBe('15h 10m')
    expect(formatDuration(605)).toBe('10h 05m')
  })

  it('shows only minutes under an hour', () => {
    expect(formatDuration(45)).toBe('45m')
  })
})

describe('toLocalInputValue', () => {
  it('formats a date for a datetime-local input', () => {
    const date = new Date(2026, 10, 20, 6, 30)
    expect(toLocalInputValue(date)).toBe('2026-11-20T06:30')
  })
})

describe('riskColor', () => {
  it('maps whole and fractional scores to their level', () => {
    expect(riskColor(0)).toBe(RISK_LEVELS[0].color)
    expect(riskColor(2.7)).toBe(RISK_LEVELS[2].color)
    expect(riskColor(9)).toBe(RISK_LEVELS[4].color)
  })
})
