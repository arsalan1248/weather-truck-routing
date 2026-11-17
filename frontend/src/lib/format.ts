const dateTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDateTime(iso: string | Date): string {
  return dateTime.format(typeof iso === 'string' ? new Date(iso) : iso)
}

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return hours ? `${hours}h ${String(rest).padStart(2, '0')}m` : `${rest}m`
}

export function formatMiles(miles: number): string {
  return `${Math.round(miles).toLocaleString()} mi`
}

// Value for <input type="datetime-local">, which works in local time without a zone.
export function toLocalInputValue(date: Date): string {
  const offsetMs = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
}

export function nextFullHour(): Date {
  const date = new Date()
  date.setHours(date.getHours() + 1, 0, 0, 0)
  return date
}
