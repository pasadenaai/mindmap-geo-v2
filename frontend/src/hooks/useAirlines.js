import { useState, useEffect } from 'react'

export function useAirlines() {
  const [airlines, setAirlines] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/airlines.json')
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setAirlines(data.airlines)
      })
      .catch(err => console.error('Failed to load airlines:', err))
    return () => { cancelled = true }
  }, [])

  return airlines
}
