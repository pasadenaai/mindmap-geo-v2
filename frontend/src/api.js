const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

function getToken() {
  try { return localStorage.getItem('geo_token') } catch { return null }
}

function authHeaders() {
  const token = getToken()
  return token
    ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' }
}

async function request(method, path, body, auth = false) {
  const headers = auth ? authHeaders() : (body ? { 'Content-Type': 'application/json' } : {})
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${method} ${path} → ${res.status}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export const auth = {
  register: (username, password) => request('POST', '/auth/register', { username, password }),
  login:    (username, password) => request('POST', '/auth/login',    { username, password }),
  me:       ()                   => request('GET',  '/auth/me',       undefined, true),
  logout:   ()                   => request('POST', '/auth/logout',   {}, false),
  refresh:  ()                   => request('POST', '/auth/refresh',  {}, false),
}

// ── Geo Points ────────────────────────────────────────────────────────────────
export const geo = {
  points: {
    list:   ()           => request('GET',    '/geo/points'),
    create: (data)       => request('POST',   '/geo/points', data),
    update: (id, data)   => request('PATCH',  `/geo/points/${id}`, data),
    delete: (id)         => request('DELETE', `/geo/points/${id}`),
  },
  arcs: {
    list:   ()           => request('GET',    '/geo/arcs'),
    create: (data)       => request('POST',   '/geo/arcs', data),
    update: (id, data)   => request('PATCH',  `/geo/arcs/${id}`, data),
    delete: (id)         => request('DELETE', `/geo/arcs/${id}`),
  },
  configs: {
    list:   ()           => request('GET',    '/geo/configs'),
    create: (data)       => request('POST',   '/geo/configs', data),
    update: (id, data)   => request('PATCH',  `/geo/configs/${id}`, data),
    delete: (id)         => request('DELETE', `/geo/configs/${id}`),
  },
  countries: {
    list:          ()      => request('GET', '/geo/countries'),
    listGlobe:     ()      => request('GET', '/geo/countries/globe'),
    getByFeature:  (ccn3)  => request('GET', `/geo/countries/by-feature/${ccn3}`),
    get:           (cca2)  => request('GET', `/geo/countries/${cca2}`),
  },
  awsRegions: {
    list: () => request('GET', '/geo/aws-regions'),
    get:  (id) => request('GET', `/geo/aws-regions/${id}`),
  },
  azureRegions: {
    list: () => request('GET', '/geo/azure-regions'),
    get:  (id) => request('GET', `/geo/azure-regions/${id}`),
  },
  gcpRegions: {
    list: () => request('GET', '/geo/gcp-regions'),
    get:  (id) => request('GET', `/geo/gcp-regions/${id}`),
  },
  alibabaRegions: {
    list: () => request('GET', '/geo/alibaba-regions'),
    get:  (id) => request('GET', `/geo/alibaba-regions/${id}`),
  },
  ociRegions: {
    list: () => request('GET', '/geo/oci-regions'),
    get:  (id) => request('GET', `/geo/oci-regions/${id}`),
  },
  ibmRegions: {
    list: () => request('GET', '/geo/ibm-regions'),
    get:  (id) => request('GET', `/geo/ibm-regions/${id}`),
  },
}
