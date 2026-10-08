import { useState, useMemo, useEffect } from 'react'
import { useGeoStore } from '../store'
import { useAirports } from '../hooks/useAirports'
import { useAirlines } from '../hooks/useAirlines'
import { useCountryElements } from '../hooks/useCountryElements'
import './DataPanel.css'

const COLOR_PRESETS = ['#4fc3f7', '#f06292', '#aed581', '#ffb74d', '#ce93d8', '#80deea']

function AddPointForm({ onClose }) {
  const addPoint = useGeoStore((s) => s.addPoint)
  const [form, setForm] = useState({ label: '', lat: '', lon: '', color: '#4fc3f7' })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState(null)

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    if (!form.label || form.lat === '' || form.lon === '') return
    setSaving(true)
    setErr(null)
    try {
      await addPoint({ ...form, lat: parseFloat(form.lat), lon: parseFloat(form.lon) })
      onClose()
    } catch (ex) {
      setErr(ex.message)
      setSaving(false)
    }
  }

  return (
    <form className="add-form" onSubmit={submit}>
      <div className="form-row">
        <label>Label</label>
        <input value={form.label} onChange={(e) => set('label', e.target.value)} placeholder="e.g. New York" />
      </div>
      <div className="form-row form-row--half">
        <div>
          <label>Lat</label>
          <input type="number" step="any" value={form.lat} onChange={(e) => set('lat', e.target.value)} placeholder="40.71" />
        </div>
        <div>
          <label>Lon</label>
          <input type="number" step="any" value={form.lon} onChange={(e) => set('lon', e.target.value)} placeholder="-74.00" />
        </div>
      </div>
      <div className="form-row">
        <label>Color</label>
        <div className="color-row">
          {COLOR_PRESETS.map((c) => (
            <button
              key={c}
              type="button"
              className={`color-swatch${form.color === c ? ' active' : ''}`}
              style={{ background: c }}
              onClick={() => set('color', c)}
            />
          ))}
        </div>
      </div>
      {err && <p className="form-error">{err}</p>}
      <div className="form-actions">
        <button type="button" className="btn-ghost-sm" onClick={onClose}>Cancel</button>
        <button type="submit" className="btn-primary-sm" disabled={saving}>
          {saving ? 'Saving…' : 'Add Point'}
        </button>
      </div>
    </form>
  )
}

function PointRow({ point }) {
  const { selectedPointId, setSelectedPoint, deletePoint } = useGeoStore()
  const isSelected = selectedPointId === point.point_id

  return (
    <div
      className={`point-row${isSelected ? ' point-row--selected' : ''}`}
      onClick={() => setSelectedPoint(isSelected ? null : point.point_id)}
    >
      <span className="point-dot" style={{ background: point.color }} />
      <div className="point-info">
        <span className="point-label">{point.label}</span>
        <span className="point-coords">{point.lat.toFixed(2)}°, {point.lon.toFixed(2)}°</span>
      </div>
      <button
        className="point-delete"
        onClick={(e) => { e.stopPropagation(); deletePoint(point.point_id) }}
        title="Remove point"
      >
        ×
      </button>
    </div>
  )
}

// ── Country detail card ────────────────────────────────────────────────────

function CountryCard({ country }) {
  return (
    <div className="country-card">
      {country.flag_4x3 && (
        <img
          className="country-card__flag"
          src={`/${country.flag_4x3}`}
          alt={`${country.name_common} flag`}
        />
      )}
      <div className="country-card__body">
        <span className="country-card__name">{country.name_common}</span>
        <span className="country-card__official">{country.name_official}</span>
        <div className="country-card__tags">
          <span className="country-tag">{country.region}</span>
          {country.subregion && <span className="country-tag country-tag--sub">{country.subregion}</span>}
        </div>
        <div className="country-card__codes">
          <span>{country.cca2}</span>
          <span>·</span>
          <span>{country.cca3}</span>
          {country.ccn3 && <><span>·</span><span>#{country.ccn3}</span></>}
        </div>
      </div>
    </div>
  )
}

// ── Country list row ───────────────────────────────────────────────────────

function CountryRow({ country, isSelected, onSelect }) {
  return (
    <div
      className={`country-row${isSelected ? ' country-row--selected' : ''}`}
      onClick={() => onSelect(isSelected ? null : country)}
    >
      {country.flag_1x1
        ? <img className="country-row__flag" src={`/${country.flag_1x1}`} alt="" />
        : <span className="country-row__flag-placeholder" />
      }
      <div className="country-row__info">
        <span className="country-row__name">{country.name_common}</span>
        <span className="country-row__region">{country.subregion || country.region}</span>
      </div>
      <span className="country-row__code">{country.cca2}</span>
    </div>
  )
}

// ── Regions drawer ─────────────────────────────────────────────────────────

const REGION_COLORS = {
  Africa:   '#f97316',
  Americas: '#22d3ee',
  Asia:     '#a78bfa',
  Europe:   '#34d399',
  Oceania:  '#fbbf24',
  Antarctic:'#94a3b8',
}

function RegionsDrawer({ globeCountries, selectedRegion, onSelect }) {
  const [open, setOpen] = useState(false)

  const regions = useMemo(() => {
    const counts = {}
    globeCountries.forEach(c => {
      if (c.region) counts[c.region] = (counts[c.region] || 0) + 1
    })
    return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b))
  }, [globeCountries])

  return (
    <div className="regions-drawer">
      <button className="regions-drawer__toggle" onClick={() => setOpen(v => !v)}>
        <span className="regions-drawer__label">Regions</span>
        {selectedRegion
          ? <span className="regions-drawer__active" style={{ color: REGION_COLORS[selectedRegion] ?? '#4fc3f7' }}>{selectedRegion}</span>
          : <span className="regions-drawer__hint">All</span>
        }
        <span className={`regions-chevron${open ? ' regions-chevron--open' : ''}`}>›</span>
      </button>

      {open && (
        <div className="regions-drawer__body">
          <button
            className={`region-pill${!selectedRegion ? ' region-pill--active' : ''}`}
            onClick={() => onSelect(null)}
          >
            All <span className="region-pill__count">{globeCountries.length}</span>
          </button>
          {regions.map(([region, count]) => (
            <button
              key={region}
              className={`region-pill${selectedRegion === region ? ' region-pill--active' : ''}`}
              style={selectedRegion === region ? { borderColor: REGION_COLORS[region], color: REGION_COLORS[region] } : {}}
              onClick={() => onSelect(selectedRegion === region ? null : region)}
            >
              {region} <span className="region-pill__count">{count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Element category colour map (matches periodic table palette) ──────────────

const ELEMENT_CATEGORY_COLORS = {
  'alkali metal':          '#ef4444',
  'alkaline earth metal':  '#f97316',
  'transition metal':      '#eab308',
  'post-transition metal': '#14b8a6',
  'metalloid':             '#22c55e',
  'polyatomic nonmetal':   '#3b82f6',
  'diatomic nonmetal':     '#6366f1',
  'noble gas':             '#a855f7',
  'lanthanide':            '#ec4899',
  'actinide':              '#f43f5e',
}

const RESERVE_UNIT_LABELS = {
  mt:         'metric tons',
  mt_ore:     'MT (ore)',
  mt_reo:     'MT (REO eq.)',
  mt_bauxite: 'MT (bauxite)',
  mt_tio2:    'MT (TiO₂)',
  mt_k2o:     'MT (K₂O)',
  mt_b2o3:    'MT (B₂O₃)',
  bcm:        'billion m³',
}

function formatReserves(val, unit) {
  if (val == null) return null
  const n = Number(val)
  let display
  if (n >= 1e9)      display = `${(n / 1e9).toFixed(1)}B`
  else if (n >= 1e6) display = `${(n / 1e6).toFixed(1)}M`
  else if (n >= 1e3) display = `${(n / 1e3).toFixed(1)}k`
  else               display = String(n)
  const label = RESERVE_UNIT_LABELS[unit] ?? unit ?? ''
  return label ? `${display} ${label}` : display
}

function ElementRow({ el }) {
  const pct = el.world_share_pct ?? 0
  const reserveStr = formatReserves(el.estimated_reserves, el.reserve_unit)
  const rankLabel = el.world_rank ? `#${el.world_rank}` : null
  const isProdBased = el.data_type === 'production'

  return (
    <div className="element-row">
      <div className="element-row__square">
        <span className="element-row__num">{el.atomic_number}</span>
        <span className="element-row__sym">{el.symbol}</span>
      </div>
      <div className="element-row__body">
        <div className="element-row__top">
          <span className="element-row__name">{el.name}</span>
          {rankLabel && (
            <span className={`element-row__rank${el.world_rank === 1 ? ' element-row__rank--gold' : ''}`}>
              {rankLabel}
            </span>
          )}
        </div>
        <div className="element-row__bar-wrap">
          <div className="element-row__bar" style={{ width: `${Math.min(pct, 100)}%` }} />
          <span className="element-row__pct">{pct.toFixed(1)}%</span>
          {isProdBased && <span className="element-row__prod-tag">prod.</span>}
        </div>
        {reserveStr && (
          <span className="element-row__reserves">{reserveStr}</span>
        )}
        {el.notes && <span className="element-row__notes">{el.notes}</span>}
      </div>
    </div>
  )
}

function ElementsDrawer({ cca2 }) {
  const [open, setOpen] = useState(false)
  const elements = useCountryElements(open ? cca2 : null)

  const sorted = useMemo(() => {
    if (!elements || elements.length === 0) return []
    return [...elements].sort((a, b) => (b.world_share_pct ?? 0) - (a.world_share_pct ?? 0))
  }, [elements])

  const hasData = elements && elements.length > 0
  const isLoading = open && elements === null

  return (
    <div className="country-elements-drawer">
      <button className="country-elements-drawer__toggle" onClick={() => setOpen(v => !v)}>
        <span className="country-elements-drawer__label">⚗ Elements &amp; minerals</span>
        {hasData && !open && (
          <span className="country-elements-drawer__count">{elements.length}</span>
        )}
        <span className={`regions-chevron${open ? ' regions-chevron--open' : ''}`}>›</span>
      </button>

      {open && (
        <div className="country-elements-drawer__body">
          {isLoading && <p className="element-loading">Loading…</p>}
          {!isLoading && sorted.length === 0 && (
            <p className="element-loading">No element data available for this country.</p>
          )}
          {sorted.map(el => <ElementRow key={el.atomic_number} el={el} />)}
        </div>
      )}
    </div>
  )
}

// ── Country expanded detail ────────────────────────────────────────────────

function CountryDetail({ country, airports, airlines, onClose }) {
  const { showAirports, toggleAirports, selectedAirports, toggleSelectedAirport, clearSelectedAirports } = useGeoStore()
  const [isoOpen,        setIsoOpen]        = useState(false)
  const [airportsOpen,   setAirportsOpen]   = useState(false)
  const [airportQuery,   setAirportQuery]   = useState('')
  const [airlinesOpen,   setAirlinesOpen]   = useState(false)
  const [airlineImgErrs, setAirlineImgErrs] = useState({})

  const countryAirlines = useMemo(
    () => airlines ? airlines.filter(a => a.country === country.cca2).sort((a, b) => a.name.localeCompare(b.name)) : [],
    [airlines, country.cca2]
  )

  const onAirlineImgError = (iata) => setAirlineImgErrs(e => ({ ...e, [iata]: true }))

  const countryAirports = useMemo(
    () => airports ? airports.filter(a => a.country === country.cca2).sort((a, b) => a.iata.localeCompare(b.iata)) : [],
    [airports, country.cca2]
  )

  const filteredAirports = useMemo(() => {
    const q = airportQuery.trim().toLowerCase()
    if (!q) return countryAirports
    return countryAirports.filter(a =>
      a.iata.toLowerCase().includes(q) ||
      a.name.toLowerCase().includes(q) ||
      (a.city || '').toLowerCase().includes(q)
    )
  }, [countryAirports, airportQuery])

  return (
    <div className="country-detail">
      <button className="country-detail__close" onClick={onClose} title="Deselect">×</button>
      {country.flag_4x3 && (
        <img
          className="country-detail__flag"
          src={`/${country.flag_4x3}`}
          alt={`${country.name_common} flag`}
        />
      )}
      <div className="country-detail__body">
        <div className="country-detail__names">
          <span className="country-detail__name">{country.name_common}</span>
          <span className="country-detail__official">{country.name_official}</span>
        </div>
        <div className="country-detail__tags">
          <span className="country-tag">{country.region}</span>
          {country.subregion && <span className="country-tag country-tag--sub">{country.subregion}</span>}
          {country.has_globe_geometry && <span className="country-tag country-tag--globe">Globe</span>}
        </div>
        <div className="country-iso-drawer">
          <button
            className="country-iso-drawer__toggle"
            onClick={() => setIsoOpen(v => !v)}
          >
            <span className="country-iso-drawer__label">ISO / Codes</span>
            <span className={`regions-chevron${isoOpen ? ' regions-chevron--open' : ''}`}>›</span>
          </button>
          {isoOpen && (
            <div className="country-detail__codes">
              <div className="country-detail__code-row">
                <span className="country-detail__code-label">ISO alpha-2</span>
                <span className="country-detail__code-value">{country.cca2}</span>
              </div>
              <div className="country-detail__code-row">
                <span className="country-detail__code-label">ISO alpha-3</span>
                <span className="country-detail__code-value">{country.cca3}</span>
              </div>
              {country.ccn3 && (
                <div className="country-detail__code-row">
                  <span className="country-detail__code-label">ISO numeric</span>
                  <span className="country-detail__code-value">{country.ccn3}</span>
                </div>
              )}
              {country.globe_feature_id && (
                <div className="country-detail__code-row">
                  <span className="country-detail__code-label">Feature ID</span>
                  <span className="country-detail__code-value">{country.globe_feature_id}</span>
                </div>
              )}
            </div>
          )}
        </div>

        <ElementsDrawer cca2={country.cca2} />

        {countryAirlines.length > 0 && (
          <div className="country-airlines-drawer">
            <button
              className="country-airlines-drawer__toggle"
              onClick={() => setAirlinesOpen(v => !v)}
            >
              <span className="country-airlines-drawer__label">Major airlines</span>
              <span className="country-airlines-drawer__count">{countryAirlines.length}</span>
              <span className={`regions-chevron${airlinesOpen ? ' regions-chevron--open' : ''}`}>›</span>
            </button>
            {airlinesOpen && (
              <div className="country-airlines-drawer__body">
                {countryAirlines.map(a => {
                  const hasLogo = !airlineImgErrs[a.iata]
                  const allianceColor = ALLIANCE_COLORS[a.alliance]
                  return (
                    <div key={a.iata} className="airline-row">
                      <div className="airline-logo-wrap airline-row__logo">
                        {hasLogo
                          ? <img src={`/assets/airlines/${a.iata}.png`} alt={a.name} onError={() => onAirlineImgError(a.iata)} />
                          : <span className="airline-logo-wrap__fallback">{a.iata}</span>
                        }
                      </div>
                      <div className="airline-row__info">
                        <span className="airline-row__name">{a.name}</span>
                        <div className="airline-row__meta">
                          <span className="airline-row__iata">{a.iata}</span>
                          {a.hub && <span className="airline-row__hub">{a.hub}</span>}
                        </div>
                      </div>
                      {a.alliance && (
                        <span
                          className="airline-row__alliance"
                          style={{ borderColor: `${allianceColor}60`, color: allianceColor }}
                          title={ALLIANCE_LABELS[a.alliance]}
                        >
                          {a.alliance === 'star_alliance' ? '★' : a.alliance === 'oneworld' ? '1W' : 'ST'}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {countryAirports.length > 0 && (
          <div className="country-airports-drawer">
            <button
              className="country-airports-drawer__toggle"
              onClick={() => setAirportsOpen(v => !v)}
            >
              <span className="country-airports-drawer__label">✈ Major airports</span>
              <div className="airport-header-actions">
                {selectedAirports.length > 0 && (
                  <button
                    className="airport-clear-btn"
                    onClick={e => { e.stopPropagation(); clearSelectedAirports() }}
                    title="Clear all pinned airports"
                  >
                    Clear {selectedAirports.length}
                  </button>
                )}
                <button
                  className={`airport-globe-toggle${showAirports ? ' airport-globe-toggle--on' : ''}`}
                  onClick={e => { e.stopPropagation(); toggleAirports() }}
                  title={showAirports ? 'Hide airports on globe' : 'Show airports on globe'}
                >
                  {showAirports ? 'On globe' : 'Off globe'}
                </button>
              </div>
              <span className="country-airports-drawer__count">{countryAirports.length}</span>
              <span className={`regions-chevron${airportsOpen ? ' regions-chevron--open' : ''}`}>›</span>
            </button>

            {airportsOpen && (
              <>
                <input
                  className="airport-search"
                  placeholder="Search airports…"
                  value={airportQuery}
                  onChange={e => setAirportQuery(e.target.value)}
                />
                <div className="country-detail__airport-list">
                  {filteredAirports.length === 0 && (
                    <p className="empty-hint">No matches{airportQuery ? ` for "${airportQuery}"` : ''}</p>
                  )}
                  {filteredAirports.map(a => {
                    const isSelected = selectedAirports.some(s => s.iata === a.iata)
                    return (
                      <div
                        key={a.iata}
                        className={`airport-row${isSelected ? ' airport-row--selected' : ''}`}
                        onClick={() => toggleSelectedAirport(a)}
                      >
                        <span className="airport-row__iata">{a.iata}</span>
                        <div className="airport-row__info">
                          <span className="airport-row__name">{a.name}</span>
                          {a.city && <span className="airport-row__city">{a.city}</span>}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Countries tab ──────────────────────────────────────────────────────────

function CountriesTab() {
  const { globeCountries, selectedCountry, setSelectedCountry,
          selectedRegion, setSelectedRegion } = useGeoStore()
  const airports = useAirports()
  const airlines = useAirlines()
  const [query, setQuery] = useState('')
  const [listOpen, setListOpen] = useState(true)

  useEffect(() => {
    setListOpen(!selectedCountry)
  }, [selectedCountry])

  const filtered = useMemo(() => {
    let list = globeCountries
    if (selectedRegion) list = list.filter(c => c.region === selectedRegion)
    const q = query.trim().toLowerCase()
    if (!q) return list
    return list.filter(c =>
      c.name_common.toLowerCase().includes(q) ||
      c.cca2.toLowerCase().includes(q) ||
      c.cca3.toLowerCase().includes(q) ||
      (c.subregion || '').toLowerCase().includes(q) ||
      c.region.toLowerCase().includes(q)
    )
  }, [globeCountries, selectedRegion, query])

  const isFiltered = filtered.length !== globeCountries.length
  const showCompactCard = selectedCountry && listOpen
  const showExpandedDetail = selectedCountry && !listOpen

  return (
    <div className="countries-tab">
      {showCompactCard && <CountryCard country={selectedCountry} />}

      <RegionsDrawer
        globeCountries={globeCountries}
        selectedRegion={selectedRegion}
        onSelect={setSelectedRegion}
      />

      <div className="countries-search">
        <input
          className="countries-search__input"
          placeholder="Search countries…"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setListOpen(true) }}
        />
        <span className="countries-search__count">{filtered.length}</span>
      </div>

      <div className={`countries-drawer${listOpen ? ' countries-drawer--open' : ''}`}>
        <button className="countries-drawer__toggle" onClick={() => setListOpen(v => !v)}>
          <span className="countries-drawer__label">Countries</span>
          <span className="countries-drawer__count">
            {isFiltered ? `${filtered.length} of ${globeCountries.length}` : filtered.length}
          </span>
          <span className={`regions-chevron${listOpen ? ' regions-chevron--open' : ''}`}>›</span>
        </button>

        {listOpen && (
          <div className="country-list">
            {filtered.length === 0 && (
              <p className="empty-hint">No matches{query ? ` for "${query}"` : ''}</p>
            )}
            {filtered.map((c) => (
              <CountryRow
                key={c.cca2}
                country={c}
                isSelected={selectedCountry?.cca2 === c.cca2}
                onSelect={setSelectedCountry}
              />
            ))}
          </div>
        )}
      </div>

      {showExpandedDetail && (
        <CountryDetail
          country={selectedCountry}
          airports={airports}
          airlines={airlines}
          onClose={() => setSelectedCountry(null)}
        />
      )}
    </div>
  )
}

// ── Geo Data tab ───────────────────────────────────────────────────────────

function GeoDataTab() {
  const { points, arcs, loading, error } = useGeoStore()
  const [addingPoint, setAddingPoint] = useState(false)

  return (
    <>
      {loading && <p className="panel-status">Loading…</p>}
      {error   && <p className="panel-status panel-status--error">{error}</p>}

      <section className="panel-section">
        <div className="section-header">
          <span className="section-title">Points</span>
          <button className="btn-add" onClick={() => setAddingPoint((v) => !v)}>
            {addingPoint ? '–' : '+'}
          </button>
        </div>

        {addingPoint && <AddPointForm onClose={() => setAddingPoint(false)} />}

        <div className="point-list">
          {points.length === 0 && !addingPoint && (
            <p className="empty-hint">No points yet. Add one above.</p>
          )}
          {points.map((p) => <PointRow key={p.point_id} point={p} />)}
        </div>
      </section>
    </>
  )
}

// ── Cloud tab (all providers) ──────────────────────────────────────────────

// GEO_COLORS kept for legacy reference (now merged into PROVIDERS[].geoColors)
const GEO_COLORS = {
  Americas:      '#22d3ee',
  Europe:        '#34d399',
  'Asia Pacific':'#a78bfa',
  'Middle East': '#fb923c',
  Africa:        '#f97316',
  China:         '#f43f5e',
  GovCloud:      '#94a3b8',
}

// Generic grouped list shared by all providers
function ProviderGroups({ regions, selected, onSelect, accentColor, geoColors = {}, badgeKey = null, badgeLabel = null }) {
  const [openGeo, setOpenGeo] = useState(null)

  const grouped = useMemo(() => {
    const groups = {}
    regions.forEach(r => {
      if (!groups[r.geography]) groups[r.geography] = []
      groups[r.geography].push(r)
    })
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
  }, [regions])

  return (
    <div className="aws-groups">
      {grouped.map(([geo, items]) => {
        const isOpen = openGeo === geo
        const color = geoColors[geo] ?? accentColor
        return (
          <div key={geo} className="aws-group">
            <button className="aws-group__header" onClick={() => setOpenGeo(isOpen ? null : geo)}>
              <span className="aws-group__dot" style={{ background: color }} />
              <span className="aws-group__name">{geo}</span>
              <span className="aws-group__count">{items.length}</span>
              <span className={`regions-chevron${isOpen ? ' regions-chevron--open' : ''}`}>›</span>
            </button>
            {isOpen && (
              <div className="aws-group__body">
                {items.map(r => {
                  const isSelected = selected?.region_id === r.region_id
                  const badge = badgeKey && r[badgeKey]
                  return (
                    <div
                      key={r.region_id}
                      className={`aws-row${isSelected ? ' aws-row--selected' : ''}`}
                      onClick={() => onSelect(isSelected ? null : r)}
                    >
                      <span className="aws-row__id" style={{ color: accentColor }}>{r.region_id}</span>
                      <span className="aws-row__name">{r.name}</span>
                      {badge && <span className="aws-row__opt">{badgeLabel ?? String(badge)}</span>}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function ProviderCard({ region, accentColor, geoColors = {}, extraBadges = [] }) {
  if (!region) return null
  const geoColor = geoColors[region.geography] ?? accentColor
  return (
    <div className="aws-card" style={{ borderColor: `${accentColor}4d` }}>
      <div className="aws-card__id" style={{ color: accentColor }}>{region.region_id}</div>
      <div className="aws-card__name">{region.name}</div>
      <div className="aws-card__meta">
        <span className="aws-badge" style={{ borderColor: geoColor, color: geoColor }}>{region.geography}</span>
        {extraBadges.map(({ label, show, style }) =>
          show ? <span key={label} className="aws-badge" style={style}>{label}</span> : null
        )}
      </div>
      <div className="aws-card__coords">
        {region.lat.toFixed(3)}°, {region.lon.toFixed(3)}°
        <span style={{ marginLeft: 8, opacity: 0.5 }}>{region.country_cca2}</span>
      </div>
      {region.physical_location && (
        <div className="aws-card__coords" style={{ opacity: 0.6 }}>{region.physical_location}</div>
      )}
    </div>
  )
}

const GEO_SHARED = { Americas: '#22d3ee', Europe: '#34d399', 'Asia Pacific': '#a78bfa', 'Middle East': '#fb923c', Africa: '#f97316' }

const PROVIDERS = [
  { key: 'aws',     label: 'AWS',     color: '#ff9900', geoColors: { ...GEO_SHARED, China: '#f43f5e', GovCloud: '#94a3b8' } },
  { key: 'azure',   label: 'Azure',   color: '#0078d4', geoColors: GEO_SHARED },
  { key: 'gcp',     label: 'GCP',     color: '#4285f4', geoColors: GEO_SHARED },
  { key: 'alibaba', label: 'Alibaba', color: '#ff6700', geoColors: { ...GEO_SHARED, China: '#f43f5e' } },
  { key: 'oci',     label: 'OCI',     color: '#a855f7', geoColors: { ...GEO_SHARED, 'North America': '#22d3ee', 'Latin America': '#10b981', Government: '#94a3b8' } },
  { key: 'ibm',     label: 'IBM',     color: '#0f62fe', geoColors: GEO_SHARED },
]

function CloudTab() {
  const store = useGeoStore()
  const [providerKey, setProviderKey] = useState('aws')
  const p = PROVIDERS.find(x => x.key === providerKey)

  const cap = s => s.charAt(0).toUpperCase() + s.slice(1)
  const regions  = store[`${providerKey}Regions`] ?? []
  const selected = store[`selected${cap(providerKey)}Region`] ?? null
  const onSelect = store[`setSelected${cap(providerKey)}Region`]

  const extraBadges = {
    aws:     [{ label: `${selected?.az_count} AZs`, show: !!selected?.az_count }, { label: 'Opt-in', show: !!selected?.opt_in_required, style: { color: '#fb923c', borderColor: 'rgba(251,146,60,0.4)' } }],
    azure:   [{ label: 'AZs', show: !!selected?.has_az, style: { color: '#0078d4', borderColor: 'rgba(0,120,212,0.4)' } }, { label: 'Restricted', show: !!selected?.restricted, style: { color: '#fb923c', borderColor: 'rgba(251,146,60,0.4)' } }],
    gcp:     [{ label: `${selected?.zone_count} zones`, show: !!selected?.zone_count }],
    alibaba: [{ label: 'China', show: !!selected?.china_region, style: { color: '#f43f5e', borderColor: 'rgba(244,63,94,0.4)' } }],
    oci:     [{ label: selected?.realm, show: !!selected?.realm }],
    ibm:     [{ label: selected?.kind, show: !!selected?.kind }],
  }

  const badgeConfig = {
    aws:     { badgeKey: 'opt_in_required', badgeLabel: 'opt-in' },
    azure:   { badgeKey: 'restricted',      badgeLabel: 'restricted' },
    alibaba: { badgeKey: 'china_region',    badgeLabel: 'china' },
  }

  return (
    <div className="aws-tab">
      <div className="cloud-subtabs">
        {PROVIDERS.map(({ key, label, color }) => (
          <button
            key={key}
            className={`cloud-subtab${providerKey === key ? ' cloud-subtab--active' : ''}`}
            onClick={() => setProviderKey(key)}
          >
            <span className="cloud-subtab__dot" style={{ background: color }} />
            {label} <span className="cloud-subtab__count">{(store[`${key}Regions`] ?? []).length}</span>
          </button>
        ))}
      </div>
      <ProviderCard region={selected} accentColor={p.color} geoColors={p.geoColors} extraBadges={extraBadges[providerKey] ?? []} />
      <ProviderGroups regions={regions} selected={selected} onSelect={onSelect} accentColor={p.color} geoColors={p.geoColors} {...(badgeConfig[providerKey] ?? {})} />
    </div>
  )
}

// ── Airlines tab ───────────────────────────────────────────────────────────

const ALLIANCE_COLORS = {
  oneworld:      '#e03c31',
  star_alliance: '#003087',
  skyteam:       '#003DA5',
}

const ALLIANCE_LABELS = {
  oneworld:      'oneworld',
  star_alliance: 'Star Alliance',
  skyteam:       'SkyTeam',
}

function AirlineLogo({ iata, imgErrors, onImgError, className }) {
  const hasLogo = !imgErrors[iata]
  return (
    <div className={`airline-logo-wrap ${className || ''}`}>
      {hasLogo
        ? <img
            src={`/assets/airlines/${iata}.png`}
            alt={iata}
            onError={() => onImgError(iata)}
          />
        : <span className="airline-logo-wrap__fallback">{iata}</span>
      }
    </div>
  )
}

function AirlineDetail({ airline, imgErrors, onImgError, onClose }) {
  const allianceColor = ALLIANCE_COLORS[airline.alliance]
  return (
    <div className="airline-detail">
      <button className="airline-detail__close" onClick={onClose} title="Back to list">‹ Back</button>

      <div className="airline-detail__logo-wrap">
        <AirlineLogo iata={airline.iata} imgErrors={imgErrors} onImgError={onImgError} className="airline-detail__logo" />
      </div>

      <div className="airline-detail__body">
        <span className="airline-detail__name">{airline.name}</span>

        <div className="airline-detail__badges">
          <span className="airline-detail__iata">{airline.iata}</span>
          {airline.icao && <span className="airline-detail__icao">{airline.icao}</span>}
          {airline.alliance && (
            <span
              className="airline-detail__alliance"
              style={{ borderColor: `${allianceColor}60`, color: allianceColor }}
            >
              {ALLIANCE_LABELS[airline.alliance]}
            </span>
          )}
        </div>

        <div className="airline-detail__meta">
          {airline.hub && (
            <div className="airline-detail__meta-row">
              <span className="airline-detail__meta-label">Hub</span>
              <span className="airline-detail__meta-value">{airline.hub}</span>
            </div>
          )}
          <div className="airline-detail__meta-row">
            <span className="airline-detail__meta-label">Country</span>
            <span className="airline-detail__meta-value">{airline.country}</span>
          </div>
        </div>

        <div className="airline-detail__flights">
          <span className="airline-detail__flights-title">✈ Active Flights</span>
          <p className="airline-detail__flights-placeholder">
            Live flight data coming soon.
          </p>
        </div>
      </div>
    </div>
  )
}

function AirlinesTab() {
  const [airlines,         setAirlines]         = useState(null)
  const [query,            setQuery]            = useState('')
  const [sortMode,         setSortMode]         = useState('alpha')
  const [imgErrors,        setImgErrors]        = useState({})
  const [selectedAirline,  setSelectedAirline]  = useState(null)

  useEffect(() => {
    fetch('/data/airlines.json')
      .then(r => r.json())
      .then(d => setAirlines(d.airlines))
      .catch(err => console.error('Failed to load airlines:', err))
  }, [])

  const filtered = useMemo(() => {
    if (!airlines) return []
    const q = query.trim().toLowerCase()
    const list = q
      ? airlines.filter(a =>
          a.name.toLowerCase().includes(q) ||
          a.iata.toLowerCase().includes(q) ||
          (a.icao || '').toLowerCase().includes(q) ||
          a.country.toLowerCase().includes(q) ||
          (a.hub || '').toLowerCase().includes(q)
        )
      : airlines
    if (sortMode === 'alpha') return [...list].sort((a, b) => a.name.localeCompare(b.name))
    return [...list].sort((a, b) => a.country.localeCompare(b.country) || a.name.localeCompare(b.name))
  }, [airlines, query, sortMode])

  const groups = useMemo(() => {
    if (sortMode !== 'country') return null
    const g = {}
    filtered.forEach(a => {
      if (!g[a.country]) g[a.country] = []
      g[a.country].push(a)
    })
    return Object.entries(g).sort(([a], [b]) => a.localeCompare(b))
  }, [filtered, sortMode])

  const onImgError = (iata) => setImgErrors(e => ({ ...e, [iata]: true }))

  function AirlineRow({ airline }) {
    const allianceColor = ALLIANCE_COLORS[airline.alliance]
    return (
      <div className="airline-row" onClick={() => setSelectedAirline(airline)}>
        <AirlineLogo iata={airline.iata} imgErrors={imgErrors} onImgError={onImgError} className="airline-row__logo" />
        <div className="airline-row__info">
          <span className="airline-row__name">{airline.name}</span>
          <div className="airline-row__meta">
            <span className="airline-row__iata">{airline.iata}</span>
            {airline.icao && <span className="airline-row__icao">{airline.icao}</span>}
            {airline.hub && <span className="airline-row__hub">{airline.hub}</span>}
          </div>
        </div>
        {airline.alliance && (
          <span
            className="airline-row__alliance"
            style={{ borderColor: `${allianceColor}60`, color: allianceColor }}
            title={ALLIANCE_LABELS[airline.alliance]}
          >
            {airline.alliance === 'star_alliance' ? '★' : airline.alliance === 'oneworld' ? '1W' : 'ST'}
          </span>
        )}
      </div>
    )
  }

  if (!airlines) return <p className="panel-status">Loading…</p>

  if (selectedAirline) {
    return (
      <AirlineDetail
        airline={selectedAirline}
        imgErrors={imgErrors}
        onImgError={onImgError}
        onClose={() => setSelectedAirline(null)}
      />
    )
  }

  return (
    <div className="airlines-tab">
      <div className="airlines-controls">
        <input
          className="airlines-search"
          placeholder="Search airlines…"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <div className="airlines-sort">
          <button
            className={`airlines-sort-btn${sortMode === 'alpha' ? ' airlines-sort-btn--active' : ''}`}
            onClick={() => setSortMode('alpha')}
          >A–Z</button>
          <button
            className={`airlines-sort-btn${sortMode === 'country' ? ' airlines-sort-btn--active' : ''}`}
            onClick={() => setSortMode('country')}
          >Country</button>
        </div>
      </div>

      <div className="airlines-count">{filtered.length} of {airlines.length} airlines</div>

      <div className="airlines-list">
        {filtered.length === 0 && (
          <p className="empty-hint">No matches{query ? ` for "${query}"` : ''}</p>
        )}
        {sortMode === 'alpha' && filtered.map(a => (
          <AirlineRow key={a.iata} airline={a} />
        ))}
        {sortMode === 'country' && groups && groups.map(([country, items]) => (
          <div key={country} className="airline-country-group">
            <div className="airline-country-group__header">
              <span className="airline-country-group__code">{country}</span>
              <span className="airline-country-group__count">{items.length}</span>
            </div>
            {items.map(a => <AirlineRow key={a.iata} airline={a} />)}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Panel ──────────────────────────────────────────────────────────────────

export default function DataPanel() {
  const { points, globeCountries, awsRegions, azureRegions, gcpRegions, alibabaRegions, ociRegions, ibmRegions, panelOpen, togglePanel } = useGeoStore()
  const totalCloud = awsRegions.length + azureRegions.length + gcpRegions.length + alibabaRegions.length + ociRegions.length + ibmRegions.length
  const [tab, setTab] = useState('countries')

  return (
    <>
      <button className="panel-toggle" onClick={togglePanel} title={panelOpen ? 'Collapse panel' : 'Expand panel'}>
        {panelOpen ? '‹' : '›'}
      </button>

      <aside className={`data-panel${panelOpen ? '' : ' data-panel--collapsed'}`}>
        <header className="panel-header">
          <span className="panel-title">Geo Data</span>
          <span className="panel-meta">{points.length} pts · {globeCountries.length} countries · {totalCloud} cloud</span>
        </header>

        <div className="panel-tabs">
          <button className={`panel-tab${tab === 'countries' ? ' panel-tab--active' : ''}`} onClick={() => setTab('countries')}>Countries</button>
          <button className={`panel-tab${tab === 'airlines' ? ' panel-tab--active' : ''}`} onClick={() => setTab('airlines')}>Airlines</button>
          <button className={`panel-tab${tab === 'cloud' ? ' panel-tab--active' : ''}`} onClick={() => setTab('cloud')}>Cloud</button>
          <button className={`panel-tab${tab === 'geodata' ? ' panel-tab--active' : ''}`} onClick={() => setTab('geodata')}>Data</button>
        </div>

        {tab === 'countries' && <CountriesTab />}
        {tab === 'airlines'  && <AirlinesTab />}
        {tab === 'cloud'     && <CloudTab />}
        {tab === 'geodata'   && <GeoDataTab />}
      </aside>
    </>
  )
}
