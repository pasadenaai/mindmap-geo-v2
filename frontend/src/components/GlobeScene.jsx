import { useRef, useMemo, useState, useCallback, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, Stars, Html } from '@react-three/drei'
import * as THREE from 'three'
import { geoContains, geoEquirectangular, geoPath, geoCentroid } from 'd3-geo'
import { useGlobePoints, latLonToVec3 } from '../hooks/useGlobePoints'
import { useOceanPoints } from '../hooks/useOceanPoints'
import { useCountryBorders } from '../hooks/useCountryBorders'
import { useStateBorders } from '../hooks/useStateBorders'
import { useCapitals } from '../hooks/useCapitals'
import { useAirports } from '../hooks/useAirports'
import { useCities } from '../hooks/useCities'
import { useCountryFeatures } from '../hooks/useCountryFeatures'
import { useGeoStore } from '../store'


function makeDotTexture() {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  grad.addColorStop(0,    'rgba(255,255,255,1)')
  grad.addColorStop(0.35, 'rgba(255,255,255,0.85)')
  grad.addColorStop(1,    'rgba(255,255,255,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, size, size)
  return new THREE.CanvasTexture(canvas)
}

// Small capital city dot with hover label
function CapitalDot({ lat, lon, label, color }) {
  const [x, y, z] = latLonToVec3(lat, lon, 2.006)
  const [hovered, setHovered] = useState(false)
  return (
    <group
      position={[x, y, z]}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[0.012, 8, 8]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {hovered && (
        <Html style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(2,10,20,0.85)',
            border: `1px solid ${color}80`,
            borderRadius: 4,
            padding: '2px 6px',
            color: '#e0f0ff',
            fontSize: 10,
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
          }}>
            {label}
          </div>
        </Html>
      )}
    </group>
  )
}

// Major city dot — lime green, shows name + population on hover
function CityDot({ city }) {
  const [x, y, z] = latLonToVec3(city.lat, city.lon, 2.006)
  const [hovered, setHovered] = useState(false)
  const pop = city.pop >= 1_000_000
    ? `${(city.pop / 1_000_000).toFixed(1)}M`
    : `${Math.round(city.pop / 1000)}k`
  return (
    <group
      position={[x, y, z]}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[0.008, 8, 8]} />
        <meshBasicMaterial color="#86efac" />
      </mesh>
      {hovered && (
        <Html style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(2,10,20,0.9)',
            border: '1px solid rgba(134,239,172,0.45)',
            borderRadius: 4,
            padding: '2px 7px',
            color: '#e0ffe8',
            fontSize: 10,
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
          }}>
            <span style={{ fontWeight: 700, color: '#86efac', marginRight: 5 }}>{city.name}</span>
            <span style={{ opacity: 0.55 }}>{pop}</span>
          </div>
        </Html>
      )}
    </group>
  )
}

// Airport dot — cyan diamond color, shows IATA + city on hover
function AirportDot({ airport }) {
  const [x, y, z] = latLonToVec3(airport.lat, airport.lon, 2.007)
  const [hovered, setHovered] = useState(false)
  return (
    <group
      position={[x, y, z]}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[0.009, 8, 8]} />
        <meshBasicMaterial color="#38bdf8" />
      </mesh>
      {hovered && (
        <Html style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(2,10,20,0.9)',
            border: '1px solid rgba(56,189,248,0.5)',
            borderRadius: 4,
            padding: '2px 7px',
            color: '#e0f8ff',
            fontSize: 10,
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
          }}>
            <span style={{ fontWeight: 700, color: '#38bdf8', marginRight: 5 }}>{airport.iata}</span>
            {airport.city && <span>{airport.city}</span>}
            <span style={{ opacity: 0.55, marginLeft: 5 }}>({airport.country})</span>
          </div>
        </Html>
      )}
    </group>
  )
}

// Persistent label + dot for the airport selected from the panel list.
// Rendered outside the showAirports gate so it always appears when set.
function SelectedAirportMarker({ airport }) {
  const [x, y, z] = latLonToVec3(airport.lat, airport.lon, 2.007)
  return (
    <group position={[x, y, z]}>
      <mesh>
        <sphereGeometry args={[0.014, 10, 10]} />
        <meshBasicMaterial color="#ffffff" />
      </mesh>
      <Html style={{ pointerEvents: 'none' }}>
        <div style={{
          background: 'rgba(2,10,20,0.92)',
          border: '1px solid rgba(56,189,248,0.7)',
          borderRadius: 5,
          padding: '3px 9px',
          color: '#e0f8ff',
          fontSize: 11,
          fontWeight: 600,
          whiteSpace: 'nowrap',
          fontFamily: 'Inter, sans-serif',
          boxShadow: '0 0 8px rgba(56,189,248,0.25)',
        }}>
          <span style={{ color: '#38bdf8', marginRight: 6 }}>{airport.iata}</span>
          {airport.name}
        </div>
      </Html>
    </group>
  )
}

// Generic cloud provider region dot
function CloudRegionDot({ region, isSelected, onClick, color }) {
  const [x, y, z] = latLonToVec3(region.lat, region.lon, 2.008)
  const [hovered, setHovered] = useState(false)
  const active = isSelected || hovered

  return (
    <group
      position={[x, y, z]}
      onClick={(e) => { e.stopPropagation(); onClick(isSelected ? null : region) }}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
      onPointerOut={() => setHovered(false)}
    >
      <mesh>
        <sphereGeometry args={[active ? 0.042 : 0.018, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={active ? 0.25 : 0} />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.018, 12, 12]} />
        <meshBasicMaterial color={isSelected ? '#ffffff' : color} />
      </mesh>
      {active && (
        <Html style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(2,10,20,0.9)',
            border: `1px solid ${color}80`,
            borderRadius: 4,
            padding: '3px 8px',
            color,
            fontSize: 10,
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
          }}>
            {region.region_id}
            <span style={{ color: `${color}99`, fontWeight: 400, marginLeft: 5 }}>
              {region.name}
            </span>
          </div>
        </Html>
      )}
    </group>
  )
}

// A single geo marker pin on the globe surface
function GeoMarker({ point, isSelected, onClick }) {
  const [x, y, z] = latLonToVec3(point.lat, point.lon)
  const color = point.color || '#4fc3f7'

  return (
    <group position={[x, y, z]} onClick={(e) => { e.stopPropagation(); onClick(point.point_id) }}>
      {/* Outer ring pulse */}
      <mesh>
        <sphereGeometry args={[isSelected ? 0.055 : 0.038, 16, 16]} />
        <meshBasicMaterial color={color} transparent opacity={isSelected ? 0.35 : 0.2} />
      </mesh>
      {/* Core dot */}
      <mesh>
        <sphereGeometry args={[0.022, 16, 16]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Label — only shown when selected */}
      {isSelected && (
        <Html style={{ pointerEvents: 'none' }}>
          <div style={{
            background: 'rgba(2,10,20,0.85)',
            border: '1px solid rgba(79,195,247,0.5)',
            borderRadius: 5,
            padding: '3px 8px',
            color: '#e0f0ff',
            fontSize: 11,
            whiteSpace: 'nowrap',
            fontFamily: 'Inter, sans-serif',
          }}>
            {point.label}
          </div>
        </Html>
      )}
    </group>
  )
}

// Animated arc between two lat/lon points
function GeoArc({ arc }) {
  const points = useMemo(() => {
    const start = new THREE.Vector3(...latLonToVec3(arc.start_lat, arc.start_lon, 2.0))
    const end   = new THREE.Vector3(...latLonToVec3(arc.end_lat,   arc.end_lon,   2.0))
    const mid   = start.clone().add(end).multiplyScalar(0.5).normalize().multiplyScalar(2.0 + arc.altitude)
    const curve = new THREE.QuadraticBezierCurve3(start, mid, end)
    return curve.getPoints(48)
  }, [arc])

  const geometry = useMemo(() => new THREE.BufferGeometry().setFromPoints(points), [points])

  return (
    <line geometry={geometry}>
      <lineBasicMaterial color={arc.color || '#4fc3f7'} transparent opacity={0.6} linewidth={1} />
    </line>
  )
}

// Shared graticule constants (used by both GraticuleHalo and GraticuleLabels)
const GRATICULE_LATS = Array.from({ length: 17 }, (_, i) => -80 + i * 10)  // -80..80 step 10
const HALO_R         = 2.05   // radius of the lat/lon line halo
const LABEL_R        = 2.42   // radius of the floating degree labels
const _DEG           = Math.PI / 180

// Renders the lat/lon grid around the globe.
// Latitude circles: separate geometries so each can change colour on hover/selection.
// Meridians: separate line geometries + invisible TubeGeometry hit-meshes so
//            each great-circle arc can also react to hover/click independently.
function GraticuleHalo() {
  const showGraticule              = useGeoStore(s => s.showGraticule)
  const graticuleHoveredLat        = useGeoStore(s => s.graticuleHoveredLat)
  const graticuleSelectedLats      = useGeoStore(s => s.graticuleSelectedLats)
  const graticuleHoveredLon        = useGeoStore(s => s.graticuleHoveredLon)
  const graticuleSelectedLons      = useGeoStore(s => s.graticuleSelectedLons)
  const setGraticuleHoveredLon     = useGeoStore(s => s.setGraticuleHoveredLon)
  const toggleGraticuleSelectedLon = useGeoStore(s => s.toggleGraticuleSelectedLon)

  // ── Latitude circles — one BufferGeometry per ring ────────────────────────
  const latGeos = useMemo(() =>
    GRATICULE_LATS.map(lat => {
      const r   = HALO_R * Math.cos(lat * _DEG)
      const y   = HALO_R * Math.sin(lat * _DEG)
      const pts = []
      for (let i = 0; i < 128; i++) {
        const a0 = (i       / 128) * 2 * Math.PI
        const a1 = ((i + 1) / 128) * 2 * Math.PI
        pts.push(r * Math.cos(a0), y, r * Math.sin(a0),
                 r * Math.cos(a1), y, r * Math.sin(a1))
      }
      const g = new THREE.BufferGeometry()
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 3))
      return { lat, geo: g }
    })
  , [])

  // ── Meridians — one line geometry + one invisible tube per great-circle ───
  // The TubeGeometry follows the exact great-circle arc, so raycasting is
  // unambiguous: each tube covers exactly one of the 36 meridians.
  const lonData = useMemo(() => {
    const LONS = Array.from({ length: 36 }, (_, i) => i * 10)   // 0..350 step 10
    return LONS.map(lon => {
      const lonRad = lon * _DEG

      // Visible line segments (pole-to-pole)
      const pts = []
      for (let i = 0; i < 64; i++) {
        const lat0 = -90 + (i       / 64) * 180
        const lat1 = -90 + ((i + 1) / 64) * 180
        const r0   = HALO_R * Math.cos(lat0 * _DEG)
        const r1   = HALO_R * Math.cos(lat1 * _DEG)
        pts.push(
          r0 * Math.cos(lonRad), HALO_R * Math.sin(lat0 * _DEG), r0 * Math.sin(lonRad),
          r1 * Math.cos(lonRad), HALO_R * Math.sin(lat1 * _DEG), r1 * Math.sin(lonRad),
        )
      }
      const lineGeo = new THREE.BufferGeometry()
      lineGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 3))

      // Invisible hit tube — traces the same arc as the visible line
      const curvePoints = Array.from({ length: 33 }, (_, i) => {
        const lat = -90 + (i / 32) * 180
        return new THREE.Vector3(
          HALO_R * Math.cos(lat * _DEG) * Math.cos(lonRad),
          HALO_R * Math.sin(lat * _DEG),
          HALO_R * Math.cos(lat * _DEG) * Math.sin(lonRad),
        )
      })
      const tubeGeo = new THREE.TubeGeometry(
        new THREE.CatmullRomCurve3(curvePoints), 32, 0.07, 4, false
      )

      return { lon, lineGeo, tubeGeo }
    })
  }, [])

  return (
    <group visible={showGraticule}>
      {/* Latitude rings — colour reacts to hover / selection from labels */}
      {latGeos.map(({ lat, geo }) => {
        const isHovered  = graticuleHoveredLat === lat
        const isSelected = graticuleSelectedLats.includes(lat)
        const isEquator  = lat === 0
        const lit        = isHovered || isSelected
        const color      = lit ? '#ffffff' : isEquator ? '#fb923c' : '#4fc3f7'
        const opacity    = lit ? (isSelected ? 0.60 : 0.38) : isEquator ? 0.55 : 0.20
        return (
          <lineSegments key={lat} geometry={geo}>
            <lineBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
          </lineSegments>
        )
      })}

      {/* Meridians — visible line + invisible tube hit-area per great-circle */}
      {lonData.map(({ lon, lineGeo, tubeGeo }) => {
        const isHovered  = graticuleHoveredLon === lon
        const isSelected = graticuleSelectedLons.includes(lon)
        const lit        = isHovered || isSelected
        const color      = lit ? '#ffffff' : '#4fc3f7'
        const opacity    = lit ? (isSelected ? 0.60 : 0.38) : 0.18
        return (
          <group key={lon}>
            <lineSegments geometry={lineGeo}>
              <lineBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} />
            </lineSegments>
            {/* Invisible tube — sole purpose is raycasting for hover / click */}
            <mesh
              geometry={tubeGeo}
              onPointerEnter={(e) => { e.stopPropagation(); setGraticuleHoveredLon(lon) }}
              onPointerLeave={() => setGraticuleHoveredLon(null)}
              onClick={(e) => { e.stopPropagation(); toggleGraticuleSelectedLon(lon) }}
            >
              <meshBasicMaterial transparent opacity={0} depthWrite={false} />
            </mesh>
          </group>
        )
      })}
    </group>
  )
}

// Latitude degree labels floating in world space.
// Placed OUTSIDE the rotating GlobeMesh group — fixed in world space as the globe spins.
//
// Interactions:
//   hover  → highlights the corresponding graticule ring (dim white, temporary)
//   click  → toggles the ring to stay dim white until clicked again
//   drag   → rotates the label column around the Y-axis (north-south pole axis)
//            A move > 4 px is treated as a drag; smaller moves are treated as clicks.
function GraticuleLabels() {
  const showGraticuleLabels        = useGeoStore(s => s.showGraticuleLabels)
  const graticuleSelectedLats      = useGeoStore(s => s.graticuleSelectedLats)
  const setGraticuleHoveredLat     = useGeoStore(s => s.setGraticuleHoveredLat)
  const toggleGraticuleSelectedLat = useGeoStore(s => s.toggleGraticuleSelectedLat)

  // Y-axis rotation angle for the label column (radians).
  const [angle,    setAngle]    = useState(0)
  const [dragging, setDragging] = useState(false)
  const angleRef  = useRef(0)
  // Single ref tracks the active drag; null when idle.
  // { startX, startAngle, lat, moved }
  const dragState = useRef(null)

  // Keep angleRef in sync so handlers always read the latest angle without
  // taking it as a dependency (which would recreate them on every rotation).
  useEffect(() => { angleRef.current = angle }, [angle])

  // ── Pointer handlers ──────────────────────────────────────────────────────
  // Using setPointerCapture means the browser sends all subsequent pointermove
  // and pointerup events to the pressed element, even when the cursor leaves it.
  // This is robust against the Three.js raycaster and the canvas's own capture.

  const onPointerDown = useCallback((lat, e) => {
    e.preventDefault()
    e.stopPropagation()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragState.current = { startX: e.clientX, startAngle: angleRef.current, lat, moved: false }
    setDragging(true)
  }, [])   // stable — no state deps; reads angle via ref

  const onPointerMove = useCallback((e) => {
    if (!dragState.current) return
    e.preventDefault()
    const dx = e.clientX - dragState.current.startX
    if (Math.abs(dx) > 4) dragState.current.moved = true
    setAngle(dragState.current.startAngle - dx * 0.006)
  }, [])   // stable

  const onPointerUp = useCallback((lat, e) => {
    if (!dragState.current) return
    // Short tap (< 4 px movement) → treat as a click and toggle selection
    if (!dragState.current.moved) toggleGraticuleSelectedLat(lat)
    dragState.current = null
    setDragging(false)
  }, [toggleGraticuleSelectedLat])

  if (!showGraticuleLabels) return null

  return GRATICULE_LATS.map((lat) => {
    const r          = LABEL_R * Math.cos(lat * _DEG)
    const x          = r * Math.cos(angle)
    const y          = LABEL_R * Math.sin(lat * _DEG)
    const z          = r * Math.sin(angle)
    const label      = lat === 0 ? '0' : `${Math.abs(lat)}`
    const hemisphere = lat > 0 ? ' N' : lat < 0 ? ' S' : ''
    const isEq       = lat === 0
    const isSelected = graticuleSelectedLats.includes(lat)

    return (
      <Html key={lat} position={[x, y, z]} style={{ pointerEvents: 'auto' }}>
        <div
          onPointerDown={(e) => onPointerDown(lat, e)}
          onPointerMove={onPointerMove}
          onPointerUp={(e) => onPointerUp(lat, e)}
          onPointerEnter={() => setGraticuleHoveredLat(lat)}
          onPointerLeave={() => setGraticuleHoveredLat(null)}
          title="Hover to highlight ring  ·  Click to pin  ·  Drag to reposition column"
          style={{
            display:        'flex',
            alignItems:     'center',
            gap:            3,
            transform:      'translateY(-50%)',
            whiteSpace:     'nowrap',
            userSelect:     'none',
            cursor:         dragging ? 'grabbing' : 'grab',
            fontFamily:     'Inter, ui-monospace, monospace',
            fontSize:       9,
            fontWeight:     isEq || isSelected ? 600 : 400,
            letterSpacing:  '0.06em',
            color:          isSelected ? '#ffffff'
                          : isEq      ? '#fb923c'
                                      : '#93c5fd',
            textShadow:     '0 0 8px rgba(0,0,0,1), 0 0 4px rgba(0,0,0,1)',
            transition:     'color 0.15s',
          }}
        >
          <span style={{ opacity: 0.35, fontSize: 7 }}>—</span>
          {label}<span style={{ opacity: 0.7 }}>°</span>
          {hemisphere && <span style={{ opacity: 0.6, fontSize: 8 }}>{hemisphere}</span>}
        </div>
      </Html>
    )
  })
}

// Build THREE line-segment geometry from a GeoJSON feature's rings.
// Runs at module scope so it's not recreated on every render.
function featureToLineGeo(feature, radius = 2.004) {
  if (!feature) return null
  const positions = []
  const geom = feature.geometry
  const polys = geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates
  for (const poly of polys) {
    for (const ring of poly) {
      for (let i = 0; i < ring.length - 1; i++) {
        const [lon1, lat1] = ring[i]
        const [lon2, lat2] = ring[i + 1]
        positions.push(...latLonToVec3(lat1, lon1, radius), ...latLonToVec3(lat2, lon2, radius))
      }
    }
  }
  if (!positions.length) return null
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  return geo
}

function GlobeMesh() {
  const groupRef        = useRef()
  const globeHovered    = useRef(false)
  const landPoints      = useGlobePoints(1.8)
  const oceanPoints     = useOceanPoints(1.75)
  const borderGeo       = useCountryBorders()
  const stateGeo        = useStateBorders()
  const capitals        = useCapitals()
  const airports        = useAirports()
  const cities          = useCities()
  const countryFeatures = useCountryFeatures()
  const dotTex          = useMemo(() => makeDotTexture(), [])

  // Canvas texture for country hover highlight.
  // d3-geo renders into a 2048×1024 equirectangular canvas; the texture is
  // applied with repeat.x=-1 / offset.x=0.5 to align lon=0 with the sphere seam.
  const hlCanvas = useMemo(() => {
    const c = document.createElement('canvas')
    c.width  = 2048
    c.height = 1024
    return c
  }, [])

  const hlTexture = useMemo(() => {
    const t = new THREE.CanvasTexture(hlCanvas)
    t.wrapS = THREE.RepeatWrapping
    return t
  }, [hlCanvas])

  const { globeCountries, selectedCountry, setSelectedCountry,
          selectedRegion, setFlyToDir,
          awsRegions, selectedAwsRegion, setSelectedAwsRegion, showAwsRegions,
          azureRegions, selectedAzureRegion, setSelectedAzureRegion, showAzureRegions,
          gcpRegions, selectedGcpRegion, setSelectedGcpRegion, showGcpRegions,
          alibabaRegions, selectedAlibabaRegion, setSelectedAlibabaRegion, showAlibabaRegions,
          ociRegions, selectedOciRegion, setSelectedOciRegion, showOciRegions,
          ibmRegions, selectedIbmRegion, setSelectedIbmRegion, showIbmRegions,
        } = useGeoStore()

  const [hoveredFeature,  setHoveredFeature]  = useState(null)
  const [selectedFeature, setSelectedFeature] = useState(null)

  // Sharp 3D outlines — rebuilt whenever hover/selection changes
  const hoveredBorderGeo  = useMemo(() => featureToLineGeo(hoveredFeature),  [hoveredFeature])
  const selectedBorderGeo = useMemo(() => featureToLineGeo(selectedFeature), [selectedFeature])

  // Sync globe highlight when selection changes from the panel
  useEffect(() => {
    if (!countryFeatures) return
    if (!selectedCountry?.globe_feature_id) { setSelectedFeature(null); return }
    const feature = countryFeatures.find(f => String(f.id) === selectedCountry.globe_feature_id)
    setSelectedFeature(feature ?? null)
  }, [selectedCountry, countryFeatures])

  // Trigger camera fly-to when selected feature changes.
  // Apply the globe group's current Y-rotation so the target direction matches
  // the actual world-space position of the country (accounting for auto-rotate).
  useEffect(() => {
    if (!selectedFeature) { setFlyToDir(null); return }
    const [lon, lat] = geoCentroid(selectedFeature)
    const [x, y, z] = latLonToVec3(lat, lon, 1)
    const vec = new THREE.Vector3(x, y, z)
    if (groupRef.current) vec.applyEuler(groupRef.current.rotation)
    setFlyToDir([vec.x, vec.y, vec.z])
  }, [selectedFeature, setFlyToDir])

  // Feature IDs for the selected region
  const regionFeatureIds = useMemo(() => {
    if (!selectedRegion) return null
    return new Set(
      globeCountries
        .filter(c => c.region === selectedRegion)
        .map(c => c.globe_feature_id)
    )
  }, [selectedRegion, globeCountries])

  useEffect(() => {
    const ctx     = hlCanvas.getContext('2d')
    const proj    = geoEquirectangular().scale(1024 / Math.PI).translate([1024, 512])
    const pathGen = geoPath(proj, ctx)
    ctx.clearRect(0, 0, 2048, 1024)

    // White outline for all countries in the selected region (drawn first, bottom layer)
    if (regionFeatureIds && countryFeatures) {
      const regionFeatures = countryFeatures.filter(f => regionFeatureIds.has(String(f.id)))
      regionFeatures.forEach(f => {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.07)'
        ctx.beginPath()
        pathGen(f)
        ctx.fill()
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)'
        ctx.lineWidth = 2
        ctx.beginPath()
        pathGen(f)
        ctx.stroke()
      })
    }

    // Yellow fill for hovered country
    if (hoveredFeature) {
      ctx.fillStyle = 'rgba(255, 235, 59, 0.65)'
      ctx.beginPath()
      pathGen(hoveredFeature)
      ctx.fill()
    }

    // Yellow fill for selected country (border rendered as 3D lineSegments)
    if (selectedFeature) {
      ctx.fillStyle = 'rgba(255, 235, 59, 0.65)'
      ctx.beginPath()
      pathGen(selectedFeature)
      ctx.fill()
    }

    hlTexture.needsUpdate = true
  }, [hoveredFeature, selectedFeature, regionFeatureIds, countryFeatures, hlCanvas, hlTexture])

  const onCountryHover = useCallback((e) => {
    e.stopPropagation()
    if (!countryFeatures || !groupRef.current) return
    const local = groupRef.current.worldToLocal(e.point.clone())
    const r   = local.length()
    const lat = 90 - Math.acos(Math.max(-1, Math.min(1, local.y / r))) * (180 / Math.PI)
    const lon = Math.atan2(local.z, -local.x) * (180 / Math.PI) - 180
    setHoveredFeature(countryFeatures.find(f => geoContains(f, [lon, lat])) ?? null)
  }, [countryFeatures])

  const onCountryOut   = useCallback(() => setHoveredFeature(null), [])
  const onCountryClick = useCallback((e) => {
    e.stopPropagation()
    if (!hoveredFeature) return
    const featureId = String(hoveredFeature.id ?? '')
    const alreadySelected = selectedCountry?.globe_feature_id === featureId
    if (alreadySelected) {
      setSelectedCountry(null)
    } else {
      const country = globeCountries.find(c => c.globe_feature_id === featureId) ?? null
      setSelectedCountry(country)
    }
  }, [hoveredFeature, selectedCountry, globeCountries, setSelectedCountry])

  const { points, arcs, selectedPointId, setSelectedPoint,
          autoRotate, toggleAutoRotate, introRotation,
          showDots, showOcean, showBorders, showStateBorders,
          showCountryCapitals, showStateCapitals, showCities, showAirports, selectedAirports, showMarkers,
          showDateLine, showPrimeMeridian, showUtcZones } = useGeoStore(s => s)

  // ── International date line (180° meridian) ──────────────────────────────
  const dateLineGeo = useMemo(() => {
    const positions = []
    const steps = 180
    for (let i = 0; i < steps; i++) {
      const lat1 = -90 + (180 * i / steps)
      const lat2 = -90 + (180 * (i + 1) / steps)
      positions.push(...latLonToVec3(lat1, 180, 2.003), ...latLonToVec3(lat2, 180, 2.003))
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [])

  // ── Prime meridian (0° longitude, Greenwich) ────────────────────────────
  const primeMeridianGeo = useMemo(() => {
    const positions = []
    const steps = 180
    for (let i = 0; i < steps; i++) {
      const lat1 = -90 + (180 * i / steps)
      const lat2 = -90 + (180 * (i + 1) / steps)
      positions.push(...latLonToVec3(lat1, 0, 2.003), ...latLonToVec3(lat2, 0, 2.003))
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [])

  // ── UTC timezone meridians (every 15°) ───────────────────────────────────
  const utcZonesGeo = useMemo(() => {
    const positions = []
    const steps = 180
    for (let lon = -165; lon <= 180; lon += 15) {
      for (let i = 0; i < steps; i++) {
        const lat1 = -90 + (180 * i / steps)
        const lat2 = -90 + (180 * (i + 1) / steps)
        positions.push(...latLonToVec3(lat1, lon, 2.003), ...latLonToVec3(lat2, lon, 2.003))
      }
    }
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    return geo
  }, [])

  const dotGeo = useMemo(() => {
    if (!landPoints) return null
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(landPoints, 3))
    return geo
  }, [landPoints])

  const oceanGeo = useMemo(() => {
    if (!oceanPoints) return null
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(oceanPoints, 3))
    return geo
  }, [oceanPoints])

  // Intro rotation: complete one full revolution (2π) on first load, then stop.
  // introDone persists across re-renders so toggling rotation back on later
  // never re-triggers the auto-stop.
  const introDone = useRef(false)
  const introAcc  = useRef(0)

  useFrame((_, delta) => {
    if (!groupRef.current || !autoRotate || globeHovered.current) return
    const isIntro = introRotation && !introDone.current
    const step    = delta * (isIntro ? 0.6 : 0.1)
    groupRef.current.rotation.y += step
    if (isIntro) {
      introAcc.current += step
      if (introAcc.current >= Math.PI * 2) {
        introDone.current = true
        toggleAutoRotate()
      }
    }
  })

  return (
    <group ref={groupRef}>
      {/* Ocean sphere — hit surface for country hover and rotation pause */}
      <mesh
        onPointerEnter={() => { globeHovered.current = true }}
        onPointerLeave={() => { globeHovered.current = false; onCountryOut() }}
        onPointerMove={onCountryHover}
        onPointerOut={onCountryOut}
        onClick={onCountryClick}
      >
        <sphereGeometry args={[1.99, 64, 64]} />
        <meshPhongMaterial color="#060f22" shininess={8} />
      </mesh>

      {/* Country hover highlight — equirectangular canvas texture mapped to sphere */}
      <mesh>
        <sphereGeometry args={[1.997, 64, 64]} />
        <meshBasicMaterial map={hlTexture} transparent alphaTest={0.01} depthWrite={false} />
      </mesh>

      {/* Sharp 3D outlines — always 1px screen-space, never magnified */}
      {hoveredBorderGeo && (
        <lineSegments geometry={hoveredBorderGeo}>
          <lineBasicMaterial color="#facc15" transparent opacity={0.9} depthWrite={false} />
        </lineSegments>
      )}
      {selectedBorderGeo && (
        <lineSegments geometry={selectedBorderGeo}>
          <lineBasicMaterial color="#ffffff" transparent opacity={0.95} depthWrite={false} />
        </lineSegments>
      )}

      {/* Wireframe grid */}
      <mesh>
        <sphereGeometry args={[1.995, 32, 16]} />
        <meshBasicMaterial color="#0d2a55" wireframe transparent opacity={0.15} />
      </mesh>

      {/* Land dots */}
      {dotGeo && (
        <points geometry={dotGeo} visible={showDots}>
          <pointsMaterial
            map={dotTex}
            color="#4fc3f7"
            size={0.022}
            sizeAttenuation
            transparent
            alphaTest={0.01}
            depthWrite={false}
          />
        </points>
      )}

      {/* Ocean dots */}
      {oceanGeo && (
        <points geometry={oceanGeo} visible={showOcean}>
          <pointsMaterial
            map={dotTex}
            color="#5090df"
            size={0.02}
            sizeAttenuation
            transparent
            opacity={0.9}
            alphaTest={0.01}
            depthWrite={false}
          />
        </points>
      )}

      {/* Country border lines */}
      {borderGeo && (
        <lineSegments geometry={borderGeo} visible={showBorders}>
          <lineBasicMaterial color="#2a7fff" transparent opacity={0.65} />
        </lineSegments>
      )}

      {/* US state border lines */}
      {stateGeo && (
        <lineSegments geometry={stateGeo} visible={showStateBorders}>
          <lineBasicMaterial color="#7ec8e3" transparent opacity={0.55} />
        </lineSegments>
      )}

      {/* UTC timezone meridians */}
      <lineSegments geometry={utcZonesGeo} visible={showUtcZones}>
        <lineBasicMaterial color="#fb923c" transparent opacity={0.35} />
      </lineSegments>

      {/* Prime meridian */}
      <lineSegments geometry={primeMeridianGeo} visible={showPrimeMeridian}>
        <lineBasicMaterial color="#34d399" transparent opacity={0.9} />
      </lineSegments>

      {/* International date line */}
      <lineSegments geometry={dateLineGeo} visible={showDateLine}>
        <lineBasicMaterial color="#facc15" transparent opacity={0.9} />
      </lineSegments>

      {/* Country capitals */}
      {capitals && showCountryCapitals && capitals.countryCapitals.map((c) => (
        <CapitalDot key={`cc-${c.country}`} lat={c.lat} lon={c.lon} label={`${c.name} (${c.country})`} color="#ef4444" />
      ))}

      {/* US state capitals */}
      {capitals && showStateCapitals && capitals.stateCapitals.map((c) => (
        <CapitalDot key={`sc-${c.state}`} lat={c.lat} lon={c.lon} label={`${c.name}, ${c.state}`} color="#ce93d8" />
      ))}

      {/* Major cities */}
      {cities && showCities && cities.map((c) => (
        <CityDot key={`${c.name}-${c.country}`} city={c} />
      ))}

      {/* Major airports */}
      {airports && showAirports && airports.map((a) => (
        <AirportDot key={a.iata} airport={a} />
      ))}

      {/* Pinned airport labels — always shown regardless of layer toggle */}
      {selectedAirports.map(a => <SelectedAirportMarker key={a.iata} airport={a} />)}

      {/* Cloud provider region dots */}
      {showAwsRegions     && awsRegions.map((r)     => <CloudRegionDot key={r.region_id} region={r} color="#ff9900" isSelected={selectedAwsRegion?.region_id     === r.region_id} onClick={setSelectedAwsRegion} />)}
      {showAzureRegions   && azureRegions.map((r)   => <CloudRegionDot key={r.region_id} region={r} color="#0078d4" isSelected={selectedAzureRegion?.region_id   === r.region_id} onClick={setSelectedAzureRegion} />)}
      {showGcpRegions     && gcpRegions.map((r)     => <CloudRegionDot key={r.region_id} region={r} color="#4285f4" isSelected={selectedGcpRegion?.region_id     === r.region_id} onClick={setSelectedGcpRegion} />)}
      {showAlibabaRegions && alibabaRegions.map((r) => <CloudRegionDot key={r.region_id} region={r} color="#ff6700" isSelected={selectedAlibabaRegion?.region_id === r.region_id} onClick={setSelectedAlibabaRegion} />)}
      {showOciRegions     && ociRegions.map((r)     => <CloudRegionDot key={r.region_id} region={r} color="#a855f7" isSelected={selectedOciRegion?.region_id     === r.region_id} onClick={setSelectedOciRegion} />)}
      {showIbmRegions     && ibmRegions.map((r)     => <CloudRegionDot key={r.region_id} region={r} color="#0f62fe" isSelected={selectedIbmRegion?.region_id     === r.region_id} onClick={setSelectedIbmRegion} />)}

      {/* Graticule halo — lat/lon grid around the globe */}
      <GraticuleHalo />

      {/* Atmosphere */}
      <mesh>
        <sphereGeometry args={[2.18, 64, 64]} />
        <meshPhongMaterial
          color="#1a6dbf"
          emissive="#0a3060"
          transparent
          opacity={0.07}
          side={THREE.BackSide}
          depthWrite={false}
        />
      </mesh>

      {/* Selected country label */}
      {selectedFeature && (() => {
        const [lon, lat] = geoCentroid(selectedFeature)
        const [x, y, z]  = latLonToVec3(lat, lon, 2.15)
        return (
          <Html position={[x, y, z]} style={{ pointerEvents: 'none' }}>
            <div style={{
              background: 'rgba(2,10,20,0.88)',
              border: '1px solid rgba(255,255,255,0.5)',
              borderRadius: 5,
              padding: '4px 12px',
              color: '#ffffff',
              fontSize: 13,
              fontWeight: 600,
              whiteSpace: 'nowrap',
              fontFamily: 'Inter, sans-serif',
              letterSpacing: '0.03em',
            }}>
              {selectedCountry?.name_common ?? selectedFeature.properties.name}
            </div>
          </Html>
        )
      })()}

      {/* Geo markers + arcs */}
      <group visible={showMarkers}>
        {points.map((p) => (
          <GeoMarker
            key={p.point_id}
            point={p}
            isSelected={selectedPointId === p.point_id}
            onClick={setSelectedPoint}
          />
        ))}
        {arcs.map((a) => (
          <GeoArc key={a.arc_id} arc={a} />
        ))}
      </group>
    </group>
  )
}

function easeInOut(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t }

function CameraFlyTo() {
  const { camera, controls } = useThree()
  const flyToDir  = useGeoStore(s => s.flyToDir)
  const targetRef   = useRef(null)
  const startRef    = useRef(null)
  const progressRef = useRef(1)

  useEffect(() => {
    if (!flyToDir) { targetRef.current = null; return }
    const [x, y, z] = flyToDir  // already world-space direction (group rotation applied)
    const target  = new THREE.Vector3(x, y, z).normalize()
    const current = camera.position.clone().normalize()
    // Nudge antipodal case to avoid degenerate lerp
    if (current.dot(target) < -0.999) target.x += 0.001
    targetRef.current   = target.normalize()
    startRef.current    = current
    progressRef.current = 0
  }, [flyToDir, camera])

  useFrame((_, delta) => {
    if (!targetRef.current || progressRef.current >= 1) return
    progressRef.current = Math.min(1, progressRef.current + delta * 1.4)
    const t      = easeInOut(progressRef.current)
    const newDir = startRef.current.clone().lerp(targetRef.current, t).normalize()
    camera.position.copy(newDir.multiplyScalar(camera.position.length()))
    controls?.update()
  })

  return null
}

const DEFAULT_DIST = 5.8
const MIN_DIST     = 3
const MAX_DIST     = 10
const ZOOM_STEP    = 0.6

const zoomBtnStyle = {
  width: 28, height: 28,
  background: 'transparent',
  border: '1px solid rgba(79,195,247,0.25)',
  borderRadius: 6,
  color: '#4fc3f7',
  fontSize: 16,
  fontWeight: 700,
  lineHeight: 1,
  cursor: 'pointer',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontFamily: 'Inter, ui-monospace, sans-serif',
  transition: 'background 0.15s',
}

function ZoomControls() {
  const { camera, controls } = useThree()
  const [pct, setPct] = useState(100)
  const lastPct = useRef(100)

  useFrame(() => {
    const next = Math.round((DEFAULT_DIST / camera.position.length()) * 100)
    if (next !== lastPct.current) {
      lastPct.current = next
      setPct(next)
    }
  })

  const applyDist = useCallback((d) => {
    camera.position.setLength(Math.max(MIN_DIST, Math.min(MAX_DIST, d)))
    controls?.update()
  }, [camera, controls])

  return (
    <Html fullscreen zIndexRange={[200, 0]} style={{ pointerEvents: 'none' }}>
      <div style={{
        position: 'absolute', bottom: 24, right: 296,
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        gap: 4, pointerEvents: 'none',
      }}>
        <div style={{
          pointerEvents: 'auto',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
          background: 'rgba(4,14,32,1)',
          border: '1px solid rgba(79,195,247,0.2)',
          borderRadius: 8,
          padding: '8px 8px',
          userSelect: 'none',
        }}>
          <button style={zoomBtnStyle} title="Zoom in"  onClick={() => applyDist(camera.position.length() - ZOOM_STEP)}>+</button>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'rgba(160,200,235,0.7)', fontFamily: 'Inter, ui-monospace, sans-serif', letterSpacing: '0.04em', minWidth: 36, textAlign: 'center' }}>
            {pct}%
          </span>
          <button style={zoomBtnStyle} title="Zoom out" onClick={() => applyDist(camera.position.length() + ZOOM_STEP)}>−</button>
          <div style={{ width: '100%', height: 1, background: 'rgba(79,195,247,0.15)', margin: '1px 0' }} />
          <button style={{ ...zoomBtnStyle, fontSize: 14 }} title="Reset zoom" onClick={() => applyDist(DEFAULT_DIST)}>⟳</button>
        </div>
      </div>
    </Html>
  )
}

function Scene() {
  return (
    <>
      <color attach="background" args={['#020a14']} />
      <Stars radius={120} depth={60} count={6000} factor={3.5} saturation={0} fade speed={0.5} />
      <ambientLight intensity={0.25} />
      <directionalLight position={[6, 4, 6]}   intensity={1.4} color="#ffffff" />
      <directionalLight position={[-6, -3, -4]} intensity={0.15} color="#4fc3f7" />
      <GlobeMesh />
      <GraticuleLabels />
      <CameraFlyTo />
      <ZoomControls />
      <OrbitControls
        makeDefault
        enableZoom={true}
        enablePan={false}
        zoomToCursor={false}
        rotateSpeed={0.45}
        minPolarAngle={Math.PI * 0.15}
        maxPolarAngle={Math.PI * 0.85}
        minDistance={3}
        maxDistance={10}
      />
    </>
  )
}

export default function GlobeScene() {
  const containerRef = useRef(null)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const prevent = (e) => { if (e.ctrlKey) e.preventDefault() }
    el.addEventListener('wheel', prevent, { passive: false })
    return () => el.removeEventListener('wheel', prevent)
  }, [])

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [0, 0, 5.8], fov: 45 }}
        gl={{ antialias: false, alpha: false }}
        dpr={[1, 2]}
      >
        <Scene />
      </Canvas>
    </div>
  )
}
