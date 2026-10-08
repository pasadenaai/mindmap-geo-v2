import { useState, useEffect } from 'react'

export function useCapitals() {
  const [capitals, setCapitals] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/capitals.json')
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setCapitals(data)
        console.log(`[capitals] ${data.countryCapitals.length} country, ${data.stateCapitals.length} state`)
      })
      .catch(err => console.error('Failed to load capitals:', err))
    return () => { cancelled = true }
  }, [])

  return capitals
}
