import { useState, useEffect } from 'react'
import { feature } from 'topojson-client'
import { geoEquirectangular, geoPath } from 'd3-geo'

const TOPO_URL = '/data/land-110m.json'
const MAP_W = 1024
const MAP_H = 512
const GLOBE_RADIUS = 2

export function useGlobePoints(step = 1.8) {
  const [points, setPoints] = useState(null)

  useEffect(() => {
    let cancelled = false

    fetch(TOPO_URL)
      .then(r => r.json())
      .then(topology => {
        if (cancelled) return

        const land = feature(topology, topology.objects.land)

        // Render land polygons to offscreen canvas → binary land mask
        const canvas = document.createElement('canvas')
        canvas.width = MAP_W
        canvas.height = MAP_H
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#000'
        ctx.fillRect(0, 0, MAP_W, MAP_H)

        const projection = geoEquirectangular()
          .scale(MAP_H / Math.PI)
          .translate([MAP_W / 2, MAP_H / 2])

        const pathGen = geoPath(projection, ctx)
        ctx.fillStyle = '#fff'
        ctx.beginPath()
        pathGen(land)
        ctx.fill()

        const { data } = ctx.getImageData(0, 0, MAP_W, MAP_H)
        const positions = []

        for (let lat = -90; lat <= 90; lat += step) {
          for (let lon = -180; lon <= 180; lon += step) {
            const [cx, cy] = projection([lon, lat])
            const px = Math.round(cx)
            const py = Math.round(cy)
            if (px < 0 || px >= MAP_W || py < 0 || py >= MAP_H) continue
            if (data[(py * MAP_W + px) * 4] < 128) continue

            const phi   = (90 - lat) * (Math.PI / 180)
            const theta = (lon + 180) * (Math.PI / 180)
            positions.push(
              -GLOBE_RADIUS * Math.sin(phi) * Math.cos(theta),
               GLOBE_RADIUS * Math.cos(phi),
               GLOBE_RADIUS * Math.sin(phi) * Math.sin(theta)
            )
          }
        }

        setPoints(new Float32Array(positions))
      })
      .catch(err => console.error('Failed to load world topology:', err))

    return () => { cancelled = true }
  }, [step])

  return points
}

// Convert lat/lon to a 3D position on the globe surface
export function latLonToVec3(lat, lon, radius = 2.05) {
  const phi   = (90 - lat) * (Math.PI / 180)
  const theta = (lon + 180) * (Math.PI / 180)
  return [
    -radius * Math.sin(phi) * Math.cos(theta),
     radius * Math.cos(phi),
     radius * Math.sin(phi) * Math.sin(theta),
  ]
}
