import test from 'node:test'
import assert from 'node:assert/strict'
import { cleanQuery, resolveCountries } from './resolve.js'
import { validateAction, runAction } from './actions.js'

const C = [
  { cca2: 'FR', cca3: 'FRA', name_common: 'France', name_official: 'French Republic', region: 'Europe', subregion: 'Western Europe', globe_feature_id: '250' },
  { cca2: 'US', cca3: 'USA', name_common: 'United States', name_official: 'United States of America', region: 'Americas', subregion: 'North America', globe_feature_id: '840' },
  { cca2: 'GB', cca3: 'GBR', name_common: 'United Kingdom', name_official: 'United Kingdom of Great Britain and Northern Ireland', region: 'Europe', subregion: 'Northern Europe', globe_feature_id: '826' },
  { cca2: 'AE', cca3: 'ARE', name_common: 'United Arab Emirates', name_official: 'United Arab Emirates', region: 'Asia', subregion: 'Western Asia', globe_feature_id: '784' },
  { cca2: 'CI', cca3: 'CIV', name_common: 'Ivory Coast', name_official: "Republic of Cote d'Ivoire", region: 'Africa', subregion: 'Western Africa', globe_feature_id: '384' },
  { cca2: 'JP', cca3: 'JPN', name_common: 'Japan', name_official: 'Japan', region: 'Asia', subregion: 'Eastern Asia', globe_feature_id: '392' },
  { cca2: 'AQ', cca3: 'ATA', name_common: 'Antarctica', name_official: 'Antarctica', region: 'Antarctic', subregion: '', globe_feature_id: null },
]
const top = q => resolveCountries(q, C)[0]?.action.cca2

test('cleanQuery strips intent phrases and filler', () => {
  assert.equal(cleanQuery('Show me the Côte d’Ivoire'), 'cote d ivoire')
  assert.equal(cleanQuery('  fly to   France '), 'france')
})

test('exact, prefix, code and alias matches rank first', () => {
  assert.equal(top('france'), 'FR')
  assert.equal(top('fra'), 'FR')        // prefix
  assert.equal(top('jp'), 'JP')         // cca2
  assert.equal(top('JPN'), 'JP')        // cca3
  assert.equal(top('usa'), 'US')        // alias
  assert.equal(top('uk'), 'GB')         // alias
  assert.equal(top('uae'), 'AE')
  assert.equal(top('ivory coast'), 'CI')
})

test('intent phrase and a one-character typo still resolve', () => {
  assert.equal(top('take me to japan'), 'JP')
  assert.equal(top('frence'), 'FR')
})

test('a single letter only matches prefixes, empty and unknown give nothing', () => {
  assert.ok(resolveCountries('u', C).every(r => /^u/i.test(r.label) || r.action.cca2.toLowerCase().startsWith('u')))
  assert.deepEqual(resolveCountries('', C), [])
  assert.deepEqual(resolveCountries('zzzzqx', C), [])
})

test('validateAction rejects unknown types, bad codes, unknown or geometry-less countries', () => {
  const ctx = { globeCountries: C }
  assert.equal(validateAction({ type: 'delete_everything' }, ctx).ok, false)
  assert.equal(validateAction({ type: 'select_country', cca2: 'FRX' }, ctx).ok, false)
  assert.equal(validateAction({ type: 'select_country', cca2: 'ZZ' }, ctx).ok, false)
  assert.equal(validateAction({ type: 'select_country', cca2: 'AQ' }, ctx).ok, false)
  assert.equal(validateAction(null, ctx).ok, false)
  assert.equal(validateAction({ type: 'select_country', cca2: 'fr' }, ctx).ok, true)   // case-insensitive
})

test('runAction re-triggers the fly-to when the country is already selected', () => {
  const calls = []
  const ctx = {
    globeCountries: C, selectedCountry: C[5],            // Japan already selected
    setSelectedCountry: c => calls.push(c ? c.cca2 : null), defer: fn => fn(),
  }
  runAction({ type: 'select_country', cca2: 'JP' }, ctx)
  assert.deepEqual(calls, [null, 'JP'])                   // cleared, then set again
  const calls2 = []
  runAction({ type: 'select_country', cca2: 'FR' }, { ...ctx, setSelectedCountry: c => calls2.push(c.cca2) })
  assert.deepEqual(calls2, ['FR'])                        // different country: single set
})

test('runAction calls the store setter only for valid actions', () => {
  const calls = []
  const ctx = { globeCountries: C, setSelectedCountry: c => calls.push(c.cca2) }
  runAction({ type: 'select_country', cca2: 'JP' }, ctx)
  runAction({ type: 'select_country', cca2: 'ZZ' }, ctx)
  runAction({ type: 'rm -rf' }, ctx)
  assert.deepEqual(calls, ['JP'])
})
