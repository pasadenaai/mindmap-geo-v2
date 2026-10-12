// Action validation + execution for the type-to-search bar.
//
// Everything that can change the UI from the bar goes through validateAction(): the input may come
// from the local resolver today or from a model tomorrow, so it is treated as UNTRUSTED. Only the
// whitelisted action types below are honoured, and each is checked against data already loaded in
// the app (a cca2 that is not in the globe country list is rejected, not guessed at).

import { ACTION_TYPES } from './resolve.js'

// Returns { ok: true, country } or { ok: false, reason }.
export function validateAction(action, { globeCountries }) {
  if (!action || typeof action !== 'object') return { ok: false, reason: 'not an action' }
  if (!ACTION_TYPES.includes(action.type)) return { ok: false, reason: `unsupported action: ${String(action.type).slice(0, 40)}` }
  if (action.type === 'select_country') {
    if (typeof action.cca2 !== 'string' || !/^[A-Za-z]{2}$/.test(action.cca2)) return { ok: false, reason: 'bad country code' }
    const country = (globeCountries || []).find(c => c.cca2 === action.cca2.toUpperCase())
    if (!country) return { ok: false, reason: 'unknown country' }
    if (!country.globe_feature_id) return { ok: false, reason: 'country has no globe geometry' }
    return { ok: true, country }
  }
  return { ok: false, reason: 'unhandled' }
}

// Applies a validated action through the store's own setters (same path as clicking in the nav).
// GlobeScene flies the camera when selectedCountry CHANGES. Re-selecting the country that is already
// selected would be a no-op (same object), so clear it first and set it on the next tick; `defer`
// is injectable so tests can run it synchronously.
export function runAction(action, { globeCountries, selectedCountry, setSelectedCountry, defer = fn => setTimeout(fn, 0) }) {
  const v = validateAction(action, { globeCountries })
  if (!v.ok) return v
  if (selectedCountry && selectedCountry.cca2 === v.country.cca2) {
    setSelectedCountry(null)
    defer(() => setSelectedCountry(v.country))
  } else {
    setSelectedCountry(v.country)
  }
  return v
}
