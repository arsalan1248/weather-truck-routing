import { useEffect, useId, useState, type KeyboardEvent } from 'react'
import { searchPlaces } from '../lib/api'
import type { Place } from '../lib/types'

interface Props {
  label: string
  placeholder: string
  value: Place | null
  onChange: (place: Place | null) => void
}

export function PlaceSearch({ label, placeholder, value, onChange }: Props) {
  const id = useId()
  const [text, setText] = useState(value?.name ?? '')
  const [suggestions, setSuggestions] = useState<Place[]>([])
  const [highlighted, setHighlighted] = useState(0)
  const [open, setOpen] = useState(false)

  const query = text.trim()
  const searching = query.length >= 3 && query !== value?.name
  const visibleSuggestions = open && searching ? suggestions : []

  useEffect(() => {
    if (!searching) return

    // Wait until typing pauses, and cancel the request if the text changes again.
    const controller = new AbortController()
    const timer = setTimeout(() => {
      searchPlaces(query, controller.signal)
        .then((places) => {
          setSuggestions(places)
          setHighlighted(0)
        })
        .catch(() => setSuggestions([]))
    }, 300)

    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query, searching])

  function choose(place: Place) {
    onChange(place)
    setText(place.name)
    setOpen(false)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    const count = visibleSuggestions.length
    if (count === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setHighlighted((i) => (i + 1) % count)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setHighlighted((i) => (i - 1 + count) % count)
    } else if (event.key === 'Enter') {
      event.preventDefault()
      choose(visibleSuggestions[highlighted])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="field place-search">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        value={text}
        placeholder={placeholder}
        autoComplete="off"
        role="combobox"
        aria-expanded={visibleSuggestions.length > 0}
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
          if (value) onChange(null)
        }}
        onKeyDown={handleKeyDown}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      />
      {visibleSuggestions.length > 0 && (
        <ul className="suggestions" role="listbox">
          {visibleSuggestions.map((place, index) => (
            <li
              key={`${place.name}-${place.lat}-${place.lon}`}
              role="option"
              aria-selected={index === highlighted}
              className={index === highlighted ? 'highlighted' : undefined}
              // mousedown fires before the input loses focus and closes the list
              onMouseDown={(event) => {
                event.preventDefault()
                choose(place)
              }}
            >
              {place.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
