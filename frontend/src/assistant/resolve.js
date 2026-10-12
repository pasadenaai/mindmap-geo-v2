// Deterministic intent resolver for the type-to-search bar (Phase 1).
//
// Pure functions only (no React, no store, no network) so they are unit-testable with `node --test`.
// A resolver takes free text plus the data already loaded in the app and returns ranked ACTION
// candidates. The action shape is the contract a future LLM-backed endpoint must also return:
//   { type: 'select_country', cca2: 'FR' }
// Anything that is not in ACTION_TYPES is rejected by the executor (see actions.js).

export const ACTION_TYPES = ['select_country']

// Spoken / informal names that are not in the country data.
const ALIASES = {
  us: 'US', usa: 'US', america: 'US', 'united states of america': 'US',
  uk: 'GB', britain: 'GB', 'great britain': 'GB', england: 'GB', scotland: 'GB', wales: 'GB',
  uae: 'AE', emirates: 'AE', holland: 'NL', burma: 'MM', 'ivory coast': 'CI', czechia: 'CZ',
  'south korea': 'KR', korea: 'KR', 'north korea': 'KP', russia: 'RU', vietnam: 'VN',
  turkey: 'TR', turkiye: 'TR', swaziland: 'SZ', macedonia: 'MK', 'east timor': 'TL',
  drc: 'CD', congo: 'CG', palestine: 'PS', syria: 'SY', iran: 'IR', laos: 'LA', brunei: 'BN',
}

// Leading verbs / filler the user may type before the place name.
const INTENT_PREFIX =
  /^(please\s+)?(show( me)?|go to|goto|fly to|take me to|open|select|find|search( for)?|zoom( in)?( to| on)?|look at|where is|navigate to|display)\s+/
const LEADING_THE = /^the\s+/

export function normalize(text) {
  return String(text ?? '')
    .normalize('NFD').replace(/[̀-ͯ]/g, '')   // strip diacritics: "Côte" -> "Cote"
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function cleanQuery(text) {
  let q = normalize(text)
  q = q.replace(INTENT_PREFIX, '').replace(LEADING_THE, '').trim()
  return q
}

function levenshtein(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    let rowMin = i
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
      rowMin = Math.min(rowMin, cur[j])
    }
    if (rowMin > max) return max + 1
    prev = cur
  }
  return prev[b.length]
}

// Score one candidate string against the query. 0 = no match.
function scoreText(q, text, { isCode = false } = {}) {
  if (!text) return 0
  if (text === q) return isCode ? 95 : 100
  if (isCode) return 0                       // codes only match exactly
  if (text.startsWith(q)) return 80 - Math.min(15, text.length - q.length)
  if (text.split(' ').some(w => w.startsWith(q))) return 65
  if (q.length >= 3 && text.includes(q)) return 45
  if (q.length >= 4) {
    const d = levenshtein(q, text.slice(0, q.length + 1), 1)   // one typo against the same-length prefix
    if (d <= 1) return 30
  }
  return 0
}

// Returns up to `limit` ranked actions: [{ action, label, detail, score }]
export function resolveCountries(rawQuery, countries, limit = 6) {
  const q = cleanQuery(rawQuery)
  if (!q || !Array.isArray(countries)) return []

  const aliasCca2 = ALIASES[q]
  const out = []
  for (const c of countries) {
    if (!c?.cca2) continue
    let best = 0
    if (aliasCca2 && c.cca2 === aliasCca2) best = 98
    best = Math.max(
      best,
      scoreText(q, normalize(c.name_common)),
      scoreText(q, normalize(c.name_official)) - 5,
      scoreText(q, normalize(c.cca2), { isCode: true }),
      scoreText(q, normalize(c.cca3), { isCode: true }),
    )
    if (best > 0) {
      out.push({
        action: { type: 'select_country', cca2: c.cca2 },
        label: c.name_common,
        detail: [c.subregion || c.region, c.cca2].filter(Boolean).join(' · '),
        flag: c.flag || null,
        score: best,
      })
    }
  }
  out.sort((a, b) => b.score - a.score || a.label.length - b.label.length || a.label.localeCompare(b.label))
  return out.slice(0, limit)
}
