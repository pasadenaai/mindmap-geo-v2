import { useState, useEffect } from 'react'
import * as THREE from 'three'

// WGS84 GeoJSON — no projection inversion needed.
// PublicaMundi/MappingAPI is proxied by jsDelivr with CORS headers.
const GEOJSON_URL = '/data/us-states.json'

const RADIUS = 2.004  // above country borders (2.002) and land dots (2.0)

function toXYZ(lon, lat) {
  const phi   = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return [
    -RADIUS * Math.sin(phi) * Math.cos(theta),
     RADIUS * Math.cos(phi),
     RADIUS * Math.sin(phi) * Math.sin(theta),
  ]
}

export function useStateBorders() {
  const [geometry, setGeometry] = useState(null)

  useEffect(() => {
    let cancelled = false

    fetch(GEOJSON_URL)
      .then(r => r.json())
      .then(geojson => {
        if (cancelled) return

        const positions = []

        for (const feature of geojson.features) {
          const { type, coordinates } = feature.geometry

          // Normalize Polygon and MultiPolygon to a flat list of rings
          const rings = type === 'Polygon'
            ? coordinates
            : coordinates.flat(1)

          for (const ring of rings) {
            for (let i = 0; i < ring.length - 1; i++) {
              const [lon1, lat1] = ring[i]
              const [lon2, lat2] = ring[i + 1]
              positions.push(...toXYZ(lon1, lat1), ...toXYZ(lon2, lat2))
            }
          }
        }

        console.log(`[state borders] built ${positions.length / 6} segments`)
        const geo = new THREE.BufferGeometry()
        geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
        setGeometry(geo)
      })
      .catch(err => console.error('Failed to load state borders:', err))

    return () => { cancelled = true }
  }, [])

  return geometry
}
