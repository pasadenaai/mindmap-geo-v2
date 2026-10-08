import { useState, useRef, useEffect, useCallback } from 'react'
import { useGeoStore, useAuthStore } from '../store'
import PeriodicTable from './PeriodicTable'
import { RESOURCE_CATEGORIES } from '../data/resourceCategories'
import './TopNav.css'

// Real element symbols are 1–2 chars, capital first letter (Oil/Gas etc. are not)
const isRealElement = sym => /^[A-Z][a-z]?$/.test(sym)

// ── Shared: close-on-outside-click hook ───────────────────────────────────────
function useClickOutside(ref, onClose) {
  useEffect(() => {
    function handle(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [ref, onClose])
}

// ── Countries dropdown ────────────────────────────────────────────────────────
function CountriesMenu() {
  const { globeCountries, selectedCountry, setSelectedCountry } = useGeoStore()
  const [open, setOpen]     = useState(false)
  const [search, setSearch] = useState('')
  const wrapRef  = useRef(null)
  const inputRef = useRef(null)

  const close = useCallback(() => { setOpen(false); setSearch('') }, [])
  useClickOutside(wrapRef, close)

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
  }, [open])

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [close])

  const filtered = globeCountries.filter(c =>
    !search ||
    c.name_common?.toLowerCase().includes(search.toLowerCase()) ||
    c.cca2?.toLowerCase().includes(search.toLowerCase())
  )

  function select(country) {
    setSelectedCountry(country)
    close()
  }

  return (
    <div className="tnav-item" ref={wrapRef}>
      <button
        className={`tnav-btn${open ? ' tnav-btn--open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        Countries
        <svg className="tnav-chevron" viewBox="0 0 10 6" fill="none">
          <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>

      {open && (
        <div className="tnav-panel tnav-panel--countries" role="listbox">
          <div className="tnav-panel__search">
            <svg className="tnav-search-icon" viewBox="0 0 16 16" fill="none">
              <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M10.5 10.5l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
            <input
              ref={inputRef}
              type="text"
              placeholder="Search countries…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="tnav-search-input"
            />
            {search && (
              <button className="tnav-search-clear" onClick={() => setSearch('')}>✕</button>
            )}
          </div>

          <div className="tnav-panel__list">
            {filtered.length === 0 ? (
              <div className="tnav-empty">No countries match "{search}"</div>
            ) : filtered.map(country => (
              <button
                key={country.cca2}
                className={`tnav-country-item${selectedCountry?.cca2 === country.cca2 ? ' tnav-country-item--active' : ''}`}
                onClick={() => select(country)}
                role="option"
                aria-selected={selectedCountry?.cca2 === country.cca2}
              >
                <span className="tnav-country-flag">{country.flag || '🌐'}</span>
                <span className="tnav-country-name">{country.name_common}</span>
                <span className="tnav-country-code">{country.cca2}</span>
              </button>
            ))}
          </div>

          <div className="tnav-panel__footer">
            {filtered.length} of {globeCountries.length} countries
          </div>
        </div>
      )}
    </div>
  )
}

// ── Resources dropdown ────────────────────────────────────────────────────────
function ResourcesMenu({ onOpenPT }) {
  const [open, setOpen]     = useState(false)
  const [active, setActive] = useState(null)
  const wrapRef = useRef(null)

  const close = useCallback(() => setOpen(false), [])
  useClickOutside(wrapRef, close)

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [close])

  function handleOpenPT() {
    close()
    onOpenPT({ mode: 'table' })
  }

  return (
    <div className="tnav-item" ref={wrapRef}>
      <button
        className={`tnav-btn${open ? ' tnav-btn--open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        Resources
        <svg className="tnav-chevron" viewBox="0 0 10 6" fill="none">
          <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>

      {open && (
        <div className="tnav-panel tnav-panel--resources">
          <div className="tnav-panel__heading">Elements</div>
          <button className="tnav-resource-item tnav-resource-item--pt" onClick={handleOpenPT}>
            <span className="tnav-atom-icon">⚛</span>
            <div className="tnav-resource-body">
              <span className="tnav-resource-label tnav-resource-label--pt">
                Periodic Table
              </span>
              <span className="tnav-resource-desc">
                All 118 elements, color-coded by category
              </span>
            </div>
            <svg className="tnav-launch-icon" viewBox="0 0 12 12" fill="none">
              <path d="M2 10L10 2M10 2H5M10 2v5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>

          <div className="tnav-section-divider" />

          <div className="tnav-panel__heading">Resource Categories</div>

          {RESOURCE_CATEGORIES.map(cat => {
            const isExpanded = active === cat.id
            return (
              <div
                key={cat.id}
                className={`tnav-resource-item${isExpanded ? ' tnav-resource-item--active' : ''}${cat.phase === 2 ? ' tnav-resource-item--phase2' : ''}`}
                style={{ '--cat-color': cat.color }}
              >
                {/* Dot toggles expand */}
                <button
                  className="tnav-resource-toggle"
                  onClick={() => setActive(a => a === cat.id ? null : cat.id)}
                  aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                  <span className="tnav-resource-dot" />
                </button>

                <div className="tnav-resource-body">
                  {/* Label opens PT → By Category */}
                  <button
                    className="tnav-resource-label-btn"
                    onClick={() => { close(); onOpenPT({ mode: 'category', categoryId: cat.id }) }}
                  >
                    <span className="tnav-resource-label">
                      {cat.label}
                      {cat.phase === 2 && <span className="tnav-phase-badge">EIA live</span>}
                    </span>
                  </button>

                  {isExpanded && (
                    <>
                      <span className="tnav-resource-desc">{cat.description}</span>
                      <div className="tnav-resource-symbols">
                        {cat.symbols.map(sym => isRealElement(sym) ? (
                          <button
                            key={sym}
                            className="tnav-sym tnav-sym--btn"
                            onClick={() => { close(); onOpenPT({ mode: 'element', symbol: sym }) }}
                          >
                            {sym}
                          </button>
                        ) : (
                          <span key={sym} className="tnav-sym">{sym}</span>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              </div>
            )
          })}

          <div className="tnav-panel__footer">
            Globe highlight &amp; country filtering — coming in next build
          </div>
        </div>
      )}
    </div>
  )
}

// ── User menu (logout) ────────────────────────────────────────────────────────
function UserMenu() {
  const { currentUser, logout } = useAuthStore()
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)

  const close = useCallback(() => setOpen(false), [])
  useClickOutside(wrapRef, close)

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') close() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [close])

  return (
    <div className="tnav-item tnav-item--user" ref={wrapRef}>
      <button
        className={`tnav-btn tnav-btn--user${open ? ' tnav-btn--open' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
          <circle cx="12" cy="8" r="4"/>
          <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round"/>
        </svg>
        {currentUser?.username}
        <svg className="tnav-chevron" viewBox="0 0 10 6" fill="none">
          <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>

      {open && (
        <div className="tnav-panel tnav-panel--user">
          <div className="tnav-user-header">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="8" r="4"/>
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" strokeLinecap="round"/>
            </svg>
            <span className="tnav-user-name">{currentUser?.username}</span>
          </div>
          <div className="tnav-section-divider" />
          <button
            className="tnav-signout-btn"
            onClick={() => { close(); logout() }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" strokeLinecap="round"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign out
          </button>
        </div>
      )}
    </div>
  )
}

// ── TopNav root bar ───────────────────────────────────────────────────────────
export default function TopNav() {
  const [ptView, setPtView] = useState(null) // null = closed

  return (
    <>
      <nav className="tnav-root">
        <div className="tnav-brand">PasadenaAI</div>

        <div className="tnav-geo-menus">
          <CountriesMenu />
          <ResourcesMenu onOpenPT={view => setPtView(view)} />
        </div>

        <UserMenu />
      </nav>
      {ptView && <PeriodicTable initialView={ptView} onClose={() => setPtView(null)} />}
    </>
  )
}
