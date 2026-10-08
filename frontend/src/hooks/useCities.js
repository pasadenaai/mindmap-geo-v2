import { useState, useEffect } from 'react'

export function useCities() {
  const [cities, setCities] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/cities.json')
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setCities(data.cities)
        console.log(`[cities] ${data.cities.length} major cities loaded`)
      })
      .catch(err => console.error('Failed to load cities:', err))
    return () => { cancelled = true }
  }, [])

  return cities
}
