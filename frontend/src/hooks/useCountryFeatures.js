import { useState, useEffect } from 'react'
import { feature } from 'topojson-client'

export function useCountryFeatures() {
  const [features, setFeatures] = useState(null)

  useEffect(() => {
    let cancelled = false
    fetch('/data/countries-110m.json')
      .then(r => r.json())
      .then(topology => {
        if (cancelled) return
        const collection = feature(topology, topology.objects.countries)
        setFeatures(collection.features)
        console.log(`[country features] loaded ${collection.features.length} countries`)
      })
      .catch(err => console.error('Failed to load country features:', err))
    return () => { cancelled = true }
  }, [])

  return features
}
