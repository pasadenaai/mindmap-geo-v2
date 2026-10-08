import { useState, useEffect } from 'react'

export function useAirports() {
  const [airports, setAirports] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/airports.json')
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setAirports(data.airports)
        console.log(`[airports] ${data.airports.length} large airports loaded`)
      })
      .catch(err => console.error('Failed to load airports:', err))
    return () => { cancelled = true }
  }, [])

  return airports
}
