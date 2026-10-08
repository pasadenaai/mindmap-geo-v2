import { create } from 'zustand'
import { geo, auth as authApi } from '../api'

// ── Auth Store ────────────────────────────────────────────────────────────────
export const useAuthStore = create((set, get) => ({
  currentUser: null,
  token: null,
  isLoggedIn: false,
  refreshTimer: null,

  init: async () => {
    const t = localStorage.getItem('geo_token')
    if (!t) return
    try {
      const user = await authApi.me()
      get()._saveSession({ access_token: t, user })
    } catch {
      await get().tryRefresh()
    }
  },

  login: async (username, password) => {
    const resp = await authApi.login(username, password)
    get()._saveSession(resp)
  },

  register: async (username, password) => {
    const resp = await authApi.register(username, password)
    get()._saveSession(resp)
  },

  logout: async () => {
    try { await authApi.logout() } catch {}
    get()._clearSession()
  },

  tryRefresh: async () => {
    try {
      const resp = await authApi.refresh()
      get()._saveSession(resp)
      return true
    } catch {
      get()._clearSession()
      return false
    }
  },

  _saveSession: (resp) => {
    localStorage.setItem('geo_token', resp.access_token)
    set({ token: resp.access_token, currentUser: resp.user, isLoggedIn: true })
    get()._scheduleRefresh(resp.access_token)
  },

  _clearSession: () => {
    localStorage.removeItem('geo_token')
    const { refreshTimer } = get()
    if (refreshTimer) clearTimeout(refreshTimer)
    set({ token: null, currentUser: null, isLoggedIn: false, refreshTimer: null })
  },

  _scheduleRefresh: (token) => {
    const { refreshTimer } = get()
    if (refreshTimer) clearTimeout(refreshTimer)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]))
      const refreshAt = payload.exp * 1000 - Date.now() - 60_000
      if (refreshAt > 0) {
        const timer = setTimeout(() => get().tryRefresh(), refreshAt)
        set({ refreshTimer: timer })
      } else {
        get().tryRefresh()
      }
    } catch {}
  },
}))

// ── Geo Store ─────────────────────────────────────────────────────────────────
export const useGeoStore = create((set, get) => ({
  // ── State ────────────────────────────────────────────────────────────────
  points: [],
  arcs: [],
  activeConfig: null,
  loading: false,
  error: null,

  // selected point_id for highlight on globe
  selectedPointId: null,
  setSelectedPoint: (id) => set({ selectedPointId: id }),

  // countries reference data (174 globe-renderable countries, sorted A→Z)
  globeCountries: [],
  loadGlobeCountries: async () => {
    try {
      const countries = await geo.countries.listGlobe()
      set({ globeCountries: countries })
    } catch (e) {
      console.error('Failed to load globe countries:', e)
    }
  },

  // country selected via globe click or panel list click
  selectedCountry: null,
  setSelectedCountry: (country) => set({ selectedCountry: country }),

  // World-space unit direction [x,y,z] to fly the camera toward; null = no pending fly
  flyToDir: null,
  setFlyToDir: (dir) => set({ flyToDir: dir }),

  // region filter — outlines all countries in the region on the globe
  selectedRegion: null,
  setSelectedRegion: (region) => set({ selectedRegion: region }),

  // AWS regions
  awsRegions: [],
  loadAwsRegions: async () => {
    try {
      const awsRegions = await geo.awsRegions.list()
      set({ awsRegions })
    } catch (e) {
      console.error('Failed to load AWS regions:', e)
    }
  },
  selectedAwsRegion: null,
  setSelectedAwsRegion: (r) => set({ selectedAwsRegion: r }),
  showAwsRegions: true,
  toggleAwsRegions: () => set((s) => ({ showAwsRegions: !s.showAwsRegions })),

  // Azure regions
  azureRegions: [],
  loadAzureRegions: async () => {
    try {
      const azureRegions = await geo.azureRegions.list()
      set({ azureRegions })
    } catch (e) {
      console.error('Failed to load Azure regions:', e)
    }
  },
  selectedAzureRegion: null,
  setSelectedAzureRegion: (r) => set({ selectedAzureRegion: r }),
  showAzureRegions: true,
  toggleAzureRegions: () => set((s) => ({ showAzureRegions: !s.showAzureRegions })),

  // GCP regions
  gcpRegions: [],
  loadGcpRegions: async () => {
    try { set({ gcpRegions: await geo.gcpRegions.list() }) } catch (e) { console.error('Failed to load GCP regions:', e) }
  },
  selectedGcpRegion: null,
  setSelectedGcpRegion: (r) => set({ selectedGcpRegion: r }),
  showGcpRegions: true,
  toggleGcpRegions: () => set((s) => ({ showGcpRegions: !s.showGcpRegions })),

  // Alibaba regions
  alibabaRegions: [],
  loadAlibabaRegions: async () => {
    try { set({ alibabaRegions: await geo.alibabaRegions.list() }) } catch (e) { console.error('Failed to load Alibaba regions:', e) }
  },
  selectedAlibabaRegion: null,
  setSelectedAlibabaRegion: (r) => set({ selectedAlibabaRegion: r }),
  showAlibabaRegions: true,
  toggleAlibabaRegions: () => set((s) => ({ showAlibabaRegions: !s.showAlibabaRegions })),

  // OCI regions
  ociRegions: [],
  loadOciRegions: async () => {
    try { set({ ociRegions: await geo.ociRegions.list() }) } catch (e) { console.error('Failed to load OCI regions:', e) }
  },
  selectedOciRegion: null,
  setSelectedOciRegion: (r) => set({ selectedOciRegion: r }),
  showOciRegions: true,
  toggleOciRegions: () => set((s) => ({ showOciRegions: !s.showOciRegions })),

  // IBM regions
  ibmRegions: [],
  loadIbmRegions: async () => {
    try { set({ ibmRegions: await geo.ibmRegions.list() }) } catch (e) { console.error('Failed to load IBM regions:', e) }
  },
  selectedIbmRegion: null,
  setSelectedIbmRegion: (r) => set({ selectedIbmRegion: r }),
  showIbmRegions: true,
  toggleIbmRegions: () => set((s) => ({ showIbmRegions: !s.showIbmRegions })),

  // panel open state
  panelOpen: true,
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),

  // ── Layer visibility ──────────────────────────────────────────────────────
  autoRotate:           true,
  toggleAutoRotate:     () => set((s) => ({ autoRotate: !s.autoRotate })),

  introRotation:        true,
  toggleIntroRotation:  () => set((s) => ({ introRotation: !s.introRotation })),

  showDots:             true,
  showOcean:            false,
  showBorders:          true,
  showStateBorders:     false,
  showCountryCapitals:  false,
  showStateCapitals:    false,
  showCities:           false,
  showAirports:         false,
  selectedAirports:     [],
  toggleSelectedAirport: (airport) => set((s) => ({
    selectedAirports: s.selectedAirports.some(a => a.iata === airport.iata)
      ? s.selectedAirports.filter(a => a.iata !== airport.iata)
      : [...s.selectedAirports, airport],
  })),
  clearSelectedAirports: () => set({ selectedAirports: [] }),
  showMarkers:          true,
  showDateLine:         false,
  showPrimeMeridian:    false,
  showUtcZones:         false,
  showGraticule:        false,
  showGraticuleLabels:  false,
  graticuleHoveredLat:  null,
  graticuleSelectedLats: [],
  graticuleHoveredLon:  null,
  graticuleSelectedLons: [],
  toggleDots:             () => set((s) => ({ showDots:             !s.showDots })),
  toggleOcean:            () => set((s) => ({ showOcean:            !s.showOcean })),
  toggleBorders:          () => set((s) => ({ showBorders:          !s.showBorders })),
  toggleStateBorders:     () => set((s) => ({ showStateBorders:     !s.showStateBorders })),
  toggleCountryCapitals:  () => set((s) => ({ showCountryCapitals:  !s.showCountryCapitals })),
  toggleStateCapitals:    () => set((s) => ({ showStateCapitals:    !s.showStateCapitals })),
  toggleCities:           () => set((s) => ({ showCities:           !s.showCities })),
  toggleAirports:         () => set((s) => ({ showAirports:         !s.showAirports })),
  toggleMarkers:          () => set((s) => ({ showMarkers:          !s.showMarkers })),
  toggleDateLine:         () => set((s) => ({ showDateLine:         !s.showDateLine })),
  togglePrimeMeridian:    () => set((s) => ({ showPrimeMeridian:    !s.showPrimeMeridian })),
  toggleUtcZones:         () => set((s) => ({ showUtcZones:         !s.showUtcZones })),
  toggleGraticule:        () => set((s) => ({ showGraticule:        !s.showGraticule })),
  toggleGraticuleLabels:  () => set((s) => ({ showGraticuleLabels:  !s.showGraticuleLabels })),
  setGraticuleHoveredLat: (lat) => set({ graticuleHoveredLat: lat }),
  toggleGraticuleSelectedLat: (lat) => set((s) => ({
    graticuleSelectedLats: s.graticuleSelectedLats.includes(lat)
      ? s.graticuleSelectedLats.filter(l => l !== lat)
      : [...s.graticuleSelectedLats, lat],
  })),
  setGraticuleHoveredLon: (lon) => set({ graticuleHoveredLon: lon }),
  toggleGraticuleSelectedLon: (lon) => set((s) => ({
    graticuleSelectedLons: s.graticuleSelectedLons.includes(lon)
      ? s.graticuleSelectedLons.filter(l => l !== lon)
      : [...s.graticuleSelectedLons, lon],
  })),
  // ── Points ───────────────────────────────────────────────────────────────
  loadPoints: async () => {
    set({ loading: true, error: null })
    try {
      const points = await geo.points.list()
      set({ points, loading: false })
    } catch (e) {
      set({ error: e.message, loading: false })
    }
  },

  addPoint: async (data) => {
    const point = await geo.points.create(data)
    set((s) => ({ points: [...s.points, point] }))
    return point
  },

  updatePoint: async (id, data) => {
    const updated = await geo.points.update(id, data)
    set((s) => ({
      points: s.points.map((p) => (p.point_id === id ? updated : p)),
    }))
  },

  deletePoint: async (id) => {
    await geo.points.delete(id)
    set((s) => ({
      points: s.points.filter((p) => p.point_id !== id),
      selectedPointId: s.selectedPointId === id ? null : s.selectedPointId,
    }))
  },

  // ── Arcs ─────────────────────────────────────────────────────────────────
  loadArcs: async () => {
    try {
      const arcs = await geo.arcs.list()
      set({ arcs })
    } catch (e) {
      console.error('Failed to load arcs:', e)
    }
  },

  addArc: async (data) => {
    const arc = await geo.arcs.create(data)
    set((s) => ({ arcs: [...s.arcs, arc] }))
    return arc
  },

  deleteArc: async (id) => {
    await geo.arcs.delete(id)
    set((s) => ({ arcs: s.arcs.filter((a) => a.arc_id !== id) }))
  },
}))
