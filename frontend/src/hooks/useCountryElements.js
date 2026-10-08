import { useState, useEffect } from 'react'

/**
 * Fetch the element-reserve profile for a country by ISO alpha-2 code.
 * Returns null while loading, [] if no data found, or an array of element records.
 */
export function useCountryElements(cca2) {
  const [elements, setElements] = useState(null)

  useEffect(() => {
    if (!cca2) { setElements([]); return }
    let cancelled = false
    setElements(null)

    fetch(`/api/geo/elements/country/${cca2}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return
        setElements(data?.elements ?? [])
      })
      .catch(err => {
        if (!cancelled) {
          console.error('Failed to load country elements:', err)
          setElements([])
        }
      })

    return () => { cancelled = true }
  }, [cca2])

  return elements
}
