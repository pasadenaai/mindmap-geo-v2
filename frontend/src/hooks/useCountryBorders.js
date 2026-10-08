import { useState, useEffect } from 'react'
import { mesh } from 'topojson-client'
import * as THREE from 'three'

const TOPO_URL = '/data/countries-110m.json'
const RADIUS = 2.002  // just above the globe sphere to avoid z-fighting with the land dots

function toXYZ(lon, lat) {
  const phi   = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return [
    -RADIUS * Math.sin(phi) * Math.cos(theta),
     RADIUS * Math.cos(phi),
     RADIUS * Math.sin(phi) * Math.sin(theta),
  ]
}

export function useCountryBorders() {
  const [geometry, setGeometry] = useState(null)

  useEffect(() => {
    let cancelled = false

    fetch(TOPO_URL)
      .then(r => r.json())
      .then(topology => {
        if (cancelled) return

        // mesh() returns a MultiLineString of every border edge (shared edges
        // appear once, coastal edges appear once — exactly what we want)
        const borders = mesh(topology, topology.objects.countries)
        const positions = []

        for (const line of borders.coordinates) {
          for (let i = 0; i < line.length - 1; i++) {
            const [lon1, lat1] = line[i]
            const [lon2, lat2] = line[i + 1]
            positions.push(...toXYZ(lon1, lat1), ...toXYZ(lon2, lat2))
          }
        }

        console.log(`[borders] built ${positions.length / 6} line segments`)
        const geo = new THREE.BufferGeometry()
        geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
        setGeometry(geo)
      })
      .catch(err => console.error('Failed to load country borders:', err))

    return () => { cancelled = true }
  }, [])

  return geometry
}
