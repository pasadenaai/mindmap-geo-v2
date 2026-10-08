import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'

// ── Simplified Bohr shell distribution ────────────────────────────────────────
// Max electrons per shell (simplified model for visual clarity)
const MAX_PER_SHELL = [2, 8, 8, 18, 18, 32, 32]

function getShells(atomicNum, period) {
  const shells = []
  let remaining = atomicNum
  for (let i = 0; i < period && remaining > 0; i++) {
    const count = Math.min(remaining, MAX_PER_SHELL[i])
    shells.push(count)
    remaining -= count
  }
  return shells
}

// ── Orbital tilt angles per shell (Euler XYZ, radians) ───────────────────────
const TILTS = [
  [0, 0, 0],
  [Math.PI / 4, 0, 0],
  [0, Math.PI / 3, 0],
  [-Math.PI / 5, Math.PI / 6, 0],
  [Math.PI / 3, -Math.PI / 4, 0],
  [-Math.PI / 6, 0, Math.PI / 3],
  [Math.PI / 5, Math.PI / 4, -Math.PI / 6],
]

// Angular speed per shell — inner shells faster
const SPEEDS = [1.5, 1.05, 0.75, 0.55, 0.38, 0.26, 0.18]

// ── Pulsing nucleus sphere ────────────────────────────────────────────────────
function Nucleus({ color }) {
  const ref = useRef()
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    ref.current.scale.setScalar(1 + Math.sin(t * 1.9) * 0.09)
  })
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.28, 32, 32]} />
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.65}
        roughness={0.2}
        metalness={0.35}
      />
    </mesh>
  )
}

// ── Single electron orbit (ring + orbiting electrons) ─────────────────────────
function Orbit({ radius, tilt, electronCount, speed, color }) {
  const refs = useRef([])
  // Cap visual electrons per ring to 8 for clarity
  const visible = Math.min(electronCount, 8)

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    refs.current.forEach((mesh, i) => {
      if (!mesh) return
      const offset = (i / visible) * Math.PI * 2
      const angle  = t * speed + offset
      mesh.position.set(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius,
        0,
      )
    })
  })

  return (
    <group rotation={tilt}>
      {/* Orbit ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[radius, 0.011, 8, 90]} />
        <meshStandardMaterial color={color} transparent opacity={0.16} />
      </mesh>
      {/* Electrons */}
      {Array.from({ length: visible }).map((_, i) => (
        <mesh key={i} ref={el => { refs.current[i] = el }}>
          <sphereGeometry args={[0.065, 10, 10]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={1.1}
            roughness={0.05}
          />
        </mesh>
      ))}
    </group>
  )
}

// ── Full atom (slow rotation wrapping all orbits + nucleus) ───────────────────
function AtomModel({ shells, color }) {
  const groupRef = useRef()

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    groupRef.current.rotation.y = t * 0.28
    groupRef.current.rotation.x = Math.sin(t * 0.14) * 0.18
  })

  return (
    <group ref={groupRef}>
      <Nucleus color={color} />
      {shells.map((count, i) => (
        <Orbit
          key={i}
          radius={(i + 1) * 0.72}
          tilt={TILTS[i % TILTS.length]}
          electronCount={count}
          speed={SPEEDS[i % SPEEDS.length]}
          color={color}
        />
      ))}
    </group>
  )
}

// ── Exported canvas ───────────────────────────────────────────────────────────
export default function AtomScene({ atomicNum, period, color }) {
  const shells = useMemo(
    () => getShells(atomicNum, Math.max(1, period)),
    [atomicNum, period],
  )

  return (
    <Canvas
      gl={{ alpha: true, antialias: true }}
      camera={{ position: [0, 0, 6.5], fov: 38 }}
      style={{ background: 'transparent' }}
    >
      <ambientLight intensity={0.22} />
      <pointLight position={[5, 5, 5]}  intensity={2.2} color="#ffffff" />
      <pointLight position={[-4, -3, -3]} intensity={0.7} color={color} />
      <AtomModel shells={shells} color={color} />
    </Canvas>
  )
}
