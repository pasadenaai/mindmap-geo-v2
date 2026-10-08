import { useState } from 'react'
import { useGeoStore } from '../store'
import './Legend.css'

const GROUPS = [
  {
    label: 'Globe',
    layers: [
      { key: 'autoRotate',        toggle: 'toggleAutoRotate',       label: 'Auto-rotate',      color: '#90caf9', icon: '↻' },
      { key: 'introRotation',     toggle: 'toggleIntroRotation',    label: 'Intro spin',       color: '#90caf9', icon: '⟳' },
      { key: 'showDots',          toggle: 'toggleDots',             label: 'Land dots',        color: '#4fc3f7', icon: '⬤' },
      { key: 'showOcean',         toggle: 'toggleOcean',            label: 'Ocean fill',       color: '#1a6dbf', icon: '⬤' },
      { key: 'showGraticule',     toggle: 'toggleGraticule',        label: 'Graticule halo',   color: '#4fc3f7', icon: '◎' },
      { key: 'showGraticuleLabels', toggle: 'toggleGraticuleLabels', label: 'Graticule labels', color: '#93c5fd', icon: '°' },
    ],
  },
  {
    label: 'Lines & Zones',
    layers: [
      { key: 'showBorders',       toggle: 'toggleBorders',          label: 'Country borders',  color: '#2a7fff', icon: '—' },
      { key: 'showStateBorders',  toggle: 'toggleStateBorders',     label: 'US state borders', color: '#7ec8e3', icon: '—' },
      { key: 'showDateLine',      toggle: 'toggleDateLine',         label: "Int'l date line",  color: '#facc15', icon: '—' },
      { key: 'showPrimeMeridian', toggle: 'togglePrimeMeridian',    label: 'Prime meridian',   color: '#34d399', icon: '—' },
      { key: 'showUtcZones',      toggle: 'toggleUtcZones',         label: 'UTC timezones',    color: '#fb923c', icon: '—' },
    ],
  },
  {
    label: 'Places',
    layers: [
      { key: 'showCountryCapitals', toggle: 'toggleCountryCapitals', label: 'Country capitals', color: '#ef4444', icon: '⬤' },
      { key: 'showStateCapitals',   toggle: 'toggleStateCapitals',   label: 'US state capitals', color: '#ce93d8', icon: '⬤' },
      { key: 'showCities',          toggle: 'toggleCities',          label: 'Major cities',     color: '#86efac', icon: '⬤' },
      { key: 'showAirports',        toggle: 'toggleAirports',        label: 'Major airports',   color: '#38bdf8', icon: '✈' },
      { key: 'showMarkers',         toggle: 'toggleMarkers',         label: 'Geo markers',      color: '#f06292', icon: '⬤' },
    ],
  },
  {
    label: 'Cloud Networks',
    layers: [
      { key: 'showAwsRegions',     toggle: 'toggleAwsRegions',     label: 'AWS regions',     color: '#ff9900', icon: '⬤' },
      { key: 'showAzureRegions',   toggle: 'toggleAzureRegions',   label: 'Azure regions',   color: '#0078d4', icon: '⬤' },
      { key: 'showGcpRegions',     toggle: 'toggleGcpRegions',     label: 'GCP regions',     color: '#4285f4', icon: '⬤' },
      { key: 'showAlibabaRegions', toggle: 'toggleAlibabaRegions', label: 'Alibaba regions', color: '#ff6700', icon: '⬤' },
      { key: 'showOciRegions',     toggle: 'toggleOciRegions',     label: 'OCI regions',     color: '#a855f7', icon: '⬤' },
      { key: 'showIbmRegions',     toggle: 'toggleIbmRegions',     label: 'IBM regions',     color: '#0f62fe', icon: '⬤' },
    ],
  },
]

function LayerRow({ layer, store }) {
  const active = store[layer.key]
  return (
    <li className={`legend__item${active ? '' : ' legend__item--off'}`}>
      <button
        className="legend__row"
        onClick={() => store[layer.toggle]()}
        title={active ? `Hide ${layer.label}` : `Show ${layer.label}`}
      >
        <span className="legend__swatch" style={{ color: layer.color }}>{layer.icon}</span>
        <span className="legend__label">{layer.label}</span>
        <span className={`legend__pill${active ? ' legend__pill--on' : ''}`}>
          <span className="legend__pill-thumb" />
        </span>
      </button>
    </li>
  )
}

export default function Legend() {
  const store = useGeoStore()
  const [open, setOpen] = useState(false)

  return (
    <div className={`legend${open ? ' legend--open' : ''}`}>
      <button className="legend__tab" onClick={() => setOpen(v => !v)}>
        <span className="legend__tab-label">Map settings</span>
        <span className={`legend__tab-chevron${open ? ' legend__tab-chevron--open' : ''}`}>‹</span>
      </button>
      <div className="legend__panel">
        {GROUPS.map(group => (
          <div key={group.label} className="legend__group">
            <span className="legend__group-label">{group.label}</span>
            <ul className="legend__list">
              {group.layers.map(layer => (
                <LayerRow key={layer.key} layer={layer} store={store} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
