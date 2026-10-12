import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useGeoStore } from '../store'
import { resolveCountries } from '../agent/resolve'
import { runAction } from '../agent/actions'
import './AgentBar.css'

// Typing any letter or digit anywhere (outside a text field) opens this bar with that character
// already entered. Enter runs the highlighted result through the validated action layer
// (agent/actions.js), which drives the same store setter the nav menus use.

function isEditable(el) {
  if (!el || el === document.body) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable === true ||
    el.getAttribute?.('role') === 'textbox'
}

export default function AgentBar() {
  const globeCountries      = useGeoStore(s => s.globeCountries)
  const selectedCountry     = useGeoStore(s => s.selectedCountry)
  const setSelectedCountry  = useGeoStore(s => s.setSelectedCountry)
  const [open, setOpen]       = useState(false)
  const [query, setQuery]     = useState('')
  const [active, setActive]   = useState(0)
  const [message, setMessage] = useState('')
  const inputRef = useRef(null)
  const wrapRef  = useRef(null)

  const close = useCallback(() => { setOpen(false); setQuery(''); setActive(0); setMessage('') }, [])

  // Global "just start typing" listener.
  useEffect(() => {
    function onKey(e) {
      if (open || e.defaultPrevented || e.isComposing) return
      if (e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key.length !== 1 || !/^[a-z0-9]$/i.test(e.key)) return
      if (isEditable(e.target) || isEditable(document.activeElement)) return
      e.preventDefault()          // the character goes into the bar, not the page
      setQuery(e.key)
      setActive(0)
      setMessage('')
      setOpen(true)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  // Focus the field with the caret after the first character.
  useEffect(() => {
    if (!open) return
    const el = inputRef.current
    if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length) }
  }, [open])

  // Click outside closes.
  useEffect(() => {
    if (!open) return
    function onDown(e) { if (wrapRef.current && !wrapRef.current.contains(e.target)) close() }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [open, close])

  const results = useMemo(() => resolveCountries(query, globeCountries), [query, globeCountries])

  function execute(result) {
    if (!result) {
      if (globeCountries.length === 0) setMessage('Countries are still loading, try again in a moment')
      else setMessage(query.trim() ? `No match for “${query.trim()}”` : '')
      return
    }
    const r = runAction(result.action, { globeCountries, selectedCountry, setSelectedCountry })
    if (r.ok) close()
    else setMessage(`Can't do that: ${r.reason}`)
  }

  function onInputKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); close() }
    else if (e.key === 'Enter') { e.preventDefault(); execute(results[active]) }
    else if (e.key === 'ArrowDown') { e.preventDefault(); setActive(i => Math.min(i + 1, Math.max(results.length - 1, 0))) }
    else if (e.key === 'ArrowUp')   { e.preventDefault(); setActive(i => Math.max(i - 1, 0)) }
  }

  if (!open) return null

  const loading = globeCountries.length === 0
  const status = loading ? 'Loading countries…'
    : results.length === 0 && query.trim() ? `No match for “${query.trim()}”`
    : `${results.length} result${results.length === 1 ? '' : 's'}`

  return (
    <div className="agentbar" ref={wrapRef} role="dialog" aria-label="Quick search">
      <div className="agentbar__field">
        <svg className="agentbar__icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <circle cx="6.5" cy="6.5" r="4.5" stroke="currentColor" strokeWidth="1.3"/>
          <path d="M10.5 10.5l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        </svg>
        <input
          ref={inputRef}
          className="agentbar__input"
          type="text"
          value={query}
          placeholder="Where to? Try “france”, “jp” or “show me the uk”"
          onChange={e => { setQuery(e.target.value); setActive(0); setMessage('') }}
          onKeyDown={onInputKey}
          role="combobox"
          aria-expanded={results.length > 0}
          aria-controls="agentbar-list"
          aria-activedescendant={results[active] ? `agentbar-opt-${active}` : undefined}
          autoComplete="off"
          spellCheck={false}
          maxLength={80}
        />
        <button className="agentbar__close" onClick={close} aria-label="Close search">✕</button>
      </div>

      {/* Always rendered so aria-controls resolves; hidden when empty. */}
      <ul className="agentbar__list" id="agentbar-list" role="listbox" hidden={results.length === 0}>
          {results.map((r, i) => (
            <li
              key={r.action.cca2}
              id={`agentbar-opt-${i}`}
              role="option"
              aria-selected={i === active}
              className={`agentbar__item${i === active ? ' agentbar__item--active' : ''}`}
              onMouseMove={() => active !== i && setActive(i)}
              onMouseDown={e => e.preventDefault()}   // keep input focus
              onClick={() => execute(r)}
            >
              <span className="agentbar__flag">{r.flag || '🌐'}</span>
              <span className="agentbar__label">{r.label}</span>
              <span className="agentbar__detail">{r.detail}</span>
            </li>
          ))}
      </ul>

      <div className="agentbar__footer" aria-live="polite">
        <span>{message || status}</span>
        <span className="agentbar__hint">↑↓ move · Enter go · Esc close</span>
      </div>
    </div>
  )
}
