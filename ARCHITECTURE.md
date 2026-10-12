# ARCHITECTURE.md — mindmap-geo

## Purpose

mindmap-geo is a dockerised geographic-visualisation service intended to be
integrated into mindmap-app-v3. It renders an interactive Three.js dot-globe
and persists geo data (points, arcs, globe configs) in DynamoDB.

## Service layout

```
browser
  └─ React/Vite (port 4203) ──── /api proxy ───► FastAPI (port 8000 → 8004 external)
                                                         │
                                               DynamoDB via LocalStack (port 4570 external)
```

## Frontend

- **Framework:** React 18 + Vite (same as mindmap-app-v3 `frontend-r`)
- **State:** Zustand (`src/store/index.js`) — single `useGeoStore`
- **3D:** Three.js + `@react-three/fiber` + `@react-three/drei`
- **Globe land mask:** TopoJSON served from `public/data/land-110m.json`, rendered to
  offscreen canvas with `d3-geo`, sampled at 1.8° grid spacing → `Float32Array` XYZ
- **Ocean fill:** same land mask canvas, inverse pixel sampling at 2.5° grid
- **Country borders:** TopoJSON `mesh()` → `LineSegments` at radius 2.002
- **US state borders:** GeoJSON (WGS84) from PublicaMundi → `LineSegments` at radius 2.004
- **Country hover highlight:** d3-geo renders hovered/selected feature into a 2048×1024
  equirectangular `CanvasTexture` mapped onto a sphere at radius 1.997. Both hover and
  selection show yellow fill on the texture. Borders are NOT painted on the texture.
- **Country borders (hover/selection):** `featureToLineGeo()` converts GeoJSON rings to
  `THREE.LineSegments` at radius 2.004 — always 1px screen-space, never magnified. Yellow
  (#facc15) for hover, white (#ffffff) for selection. Rebuilt via `useMemo` on feature change.
- **Country click:** selects country, shows name label via `<Html>` positioned at
  `geoCentroid` of the feature; triggers camera fly-to (see below)
- **Capitals:** `public/data/capitals.json` (245 country + 50 US state capitals with lat/lon)
  rendered as `CapitalDot` spheres with hover labels
- **Cities:** `public/data/cities.json` (1 165 cities with population ≥ 500 000, GeoNames CC-BY) —
  lime-green `CityDot` spheres at radius 2.006 with hover label showing name + formatted
  population. Join key: city `country` field = ISO alpha-2. Toggle: `showCities`.
  **Planned:** `geo_cities` DynamoDB table for city profiles (wiki summary, timezone, links)
  once the globe layer is stable. Static JSON stays as the authoritative position source;
  DynamoDB holds enrichment data keyed by `(name, country)`.
- **Airports:** `public/data/airports.json` (1 179 large airports, OurAirports dataset) —
  sky-blue `AirportDot` spheres at radius 2.007 with hover labels (IATA, city, country).
  Join key: airport `country` field = ISO alpha-2 (`cca2`). Shown in `CountryDetail`
  as a scrollable list regardless of the layer toggle state.
- **Geo markers:** `<Html>` from drei for labels; sphere meshes for dots
- **Arcs:** `THREE.QuadraticBezierCurve3` lifted by `arc.altitude` above the surface
- **Graticule halo:** toggleable lat/lon grid at radius 2.05 (`GraticuleHalo`, off by default)
  - 17 latitude circles (−80° to 80°, 10° step) — one `BufferGeometry` per ring so each
    can independently react to hover/selection colour changes from the label column
  - 36 meridians (0° to 350°, 10° step) — one `BufferGeometry` line + one invisible
    `TubeGeometry` hit-mesh per great-circle arc; tubes are opacity-0 but fully raycasted
  - Equator ring: amber (`#fb923c`); all other rings/meridians: blue (`#4fc3f7`)
  - Hover → dim white (0.38 opacity); click-to-pin → brighter white (0.60), toggled off on re-click
  - Pole axis is **Y** (north pole = `[0, +r, 0]`, south pole = `[0, −r, 0]`); camera at `[0, 0, 5.8]`
- **Reference meridians:** three named lines generated from pure math via `useMemo` (no data file):
  - **Prime Meridian** — green (#34d399), 0° longitude, through Greenwich/England; 90% opacity
  - **International Date Line** — gold (#facc15), 180° longitude, Pacific Ocean; 90% opacity
  - **UTC timezone grid** — amber (#fb923c), 24 meridians every 15°, 35% opacity
  - All three rendered as `LineSegments` at radius 2.003 using `latLonToVec3`, 180 segments per arc
  - IDL and Prime Meridian render above the UTC grid so they remain distinct when all three are on
- **Countries panel — collapsible drawer:** country list lives inside a toggle drawer (`CountriesDrawer`).
  Selecting a country auto-collapses the drawer and shows `CountryDetail` (expanded view). Typing
  in the search input auto-opens the drawer. Deselecting restores the open list. State driven by
  `useEffect` on `selectedCountry` + `onChange` on the search input — no external state needed.
- **Country detail view (`CountryDetail`):** full-width 4:3 flag, large name, official name, region/subregion
  tags, "Globe" badge when `has_globe_geometry=true`, ISO codes table (alpha-2, alpha-3, numeric,
  feature ID). Compact `CountryCard` shown only when the drawer is open and a country is selected.
- **Graticule labels:** toggleable degree labels floating in world space (`GraticuleLabels`, off by default)
  - 17 `<Html>` labels placed OUTSIDE the rotating group — stay fixed as the globe auto-rotates
  - Positioned at `[r·cos(θ), LABEL_R·sin(lat), r·sin(θ)]` where θ is a user-controlled Y-axis angle
  - Drag any label left/right to rotate the full column around Y (pole axis), parking labels at any
    longitude edge; uses `setPointerCapture` for reliable drag over the Three.js canvas
  - Hover label → highlights corresponding lat ring; click (< 4 px movement) → pins ring white;
    drag (≥ 4 px) → rotates column (suppresses the click/pin action)
- **Zoom controls:** `ZoomControls` component (inside Scene, rendered via `Html fullscreen`)
  - +/− buttons adjust `camera.position.length()` in 0.6-unit steps; reset snaps to 5.8
  - Live percentage: `Math.round((5.8 / camera.position.length()) * 100)` via `useFrame`
  - Pinch-to-zoom: canvas wrapper intercepts `wheel` events with `ctrlKey=true` via a
    non-passive listener, preventing browser page-zoom; `OrbitControls` handles the rest
    (`enableZoom=true`, `minDistance=3`, `maxDistance=10`, `makeDefault`)
- **Globe fly-to:** `CameraFlyTo` component (inside Scene, before OrbitControls)
  - Reads `flyToDir` from Zustand store (`[x,y,z]` world-space unit vector)
  - `GlobeMesh` writes `flyToDir` when `selectedFeature` changes: `latLonToVec3` result
    is passed through `vec.applyEuler(groupRef.current.rotation)` to account for
    accumulated auto-rotate group rotation before storing
  - Animates via ease-in-out SLERP over ~0.7s each frame, calling `controls.update()` to
    keep OrbitControls' internal spherical state in sync
- **Html label z-index:** drei `Html` defaults to `zIndexRange=[16777271,0]`. DataPanel
  sits at `z-index: 16777272` to stay above all Html overlays. `ZoomControls` uses
  `zIndexRange=[200,0]` to remain below the sidebar. `distanceFactor` removed from all
  tooltip/label `<Html>` components — labels render at fixed pixel size regardless of zoom.
- **TopNav (`TopNav.jsx` / `TopNav.css`):** navigation bar with two dropdowns:
  - `CountriesMenu` — searchable list of all globe countries; selecting one calls `setSelectedCountry` in the store
  - `ResourcesMenu` — resource categories (precious metals, battery minerals, etc.) + "Periodic Table" launcher; clicking PT sets `showPT=true` in `TopNav` state, which renders the `PeriodicTable` overlay
  - Both dropdowns close on outside click via `useClickOutside` hook; Escape key also closes
- **Periodic Table overlay (`PeriodicTable.jsx` / `PeriodicTable.css`):**
  - Rendered via `createPortal(…, document.body)` to escape `backdrop-filter` containing-block
    constraints imposed by `.top-bar` (CSS spec: `backdrop-filter ≠ none` → new fixed containing block)
  - z-index 16777274 (above DataPanel 16777272, below TopNav dropdown 16777275)
  - **Main tab bar:** Periodic Table | By Category | By Property | Statistics (static) + dynamic element tabs (one per clicked element, closeable)
  - **Grid layout:** 18-column CSS grid for periods 1–7 (main block) + separate f-block rows for lanthanides (row 9) and actinides (row 10); placeholder cells at `[6,3]` and `[7,3]`
  - **Element data:** `ELEMENTS` array — 118 entries as `[atomicNumber, symbol, name, category, row, col]`; `GRID` map for O(1) cell lookup
  - **Category colours:** 11 categories (`CAT_COLORS`) matching the app's resource palette
  - **Element profile tab:** clicking any cell opens a dynamic element tab; `ElementProfile` component shows:
    - Large 180×180px element card + category badge + property grid
    - Subtab bar: **Overview** | **Material Science** | **Scarcity** (active color = element category color via `--sub-color` CSS var)
    - **Overview subtab:** top row (card + meta + Bohr model) + Description section + News section (3 placeholder cards)
    - **Material Science subtab:** `MATERIALS_BY_SYMBOL` static lookup (~25 elements) → list of material cards (name, category badge, description); graceful fallback for unlisted elements
    - **Scarcity subtab:** placeholder pending data source
  - **Panel height:** `min-height: 640px` on `.pt-tab-content` and `.pt-el-wrap` locks the panel to the periodic table's natural height; `.pt-el-body` (`flex: 1; overflow-y: auto; min-height: 0`) makes subtab content scrollable without shrinking the panel
  - **Toolbar zone:** 48px `.pt-toolbar` reserved between tab bar and content for future search/filter controls
- **AtomScene (`AtomScene.jsx`):** React Three Fiber component rendering a 3D Bohr model atom:
  - `Canvas` with `gl={{ alpha: true }}`, transparent background, camera at z=6.5 fov=38
  - `Nucleus` — pulsing sphere (scale oscillates via `useFrame`); emissive material in element's category color
  - `Orbit` — per-shell component: `TorusGeometry` ring (opacity 0.16) + up to 8 `sphereGeometry` electrons orbiting via `useFrame`; capped at 8 visible electrons per ring for clarity
  - `AtomModel` — slow Y-rotation + X wobble wrapping all orbits and nucleus; `TILTS` array gives each shell a unique orbital plane
  - Shell fill uses simplified Bohr model: `MAX_PER_SHELL = [2,8,8,18,18,32,32]`; `getShells(atomicNum, period)` fills shells in order
  - Props: `atomicNum`, `period` (lanthanides→6, actinides→7), `color` (element category color)
- **API client:** `src/api.js` — thin fetch wrapper, proxied through Vite dev server
- **All geo data local:** `public/data/` — no CDN dependency at runtime

## Backend

- **Framework:** FastAPI 0.115 + Python 3.12
- **Storage:** DynamoDB only (no PostgreSQL — geo data is simple key-value)
- **Repo pattern:** flat async functions in `repositories/dynamo.py` (no abstract
  base needed at this scale; add one when a second storage backend is required)
- **Tables auto-created** at startup via `ensure_tables()` — safe to call repeatedly
- **No auth** — internal tool; auth will be inherited from mindmap-app-v3 when integrated

## DynamoDB tables

| Table | PK | Purpose |
|---|---|---|
| `geo_points` | `point_id` (UUID) | User-placed globe markers |
| `geo_arcs` | `arc_id` (UUID) | User-placed globe arcs |
| `geo_configs` | `config_id` (UUID) | Globe view configs |
| `geo_elements` | `atomic_number` (string "1"–"118") | Periodic table reference |
| `geo_country_elements` | `cca2` (ISO alpha-2) | Element/mineral reserves per country |
| `geo_country_resources` | `cca2` (ISO alpha-2) | Energy resources per country (Phase 2 — EIA) |
| `geo_ingest_sources` | `source_id` (string) | External data source registry |
| `geo_ingest_log` | `run_id` (UUID) | Ingestion run history |

`geo_country_elements` stores one record per country. Each entry in the `elements` list includes
`atomic_number`, `symbol`, `name`, `world_share_pct`, `estimated_reserves`, `reserve_unit`,
`world_rank`, `data_type` ("reserves"|"production"|"resources"), `notes`, and USGS provenance
fields (`_source_id`, `_data_year`, `_source_url`).
Seed source: `backend/data/country_elements.json` (63 countries, manual curation from USGS MCS 2024).
Live ingest: USGS MCS ingestor (`usgs_mcs`) overwrites reserves/world_share_pct/world_rank
from ScienceBase _world.csv files; manually-written notes are preserved by length comparison.
API: `GET /api/geo/elements/country/{cca2}`, `PUT /api/geo/elements/country/{cca2}`.

`geo_country_resources` is written by the EIA ingestor — one record per country, `resources` list
with crude oil, natural gas, coal proved reserves (value, unit, data_year, world_share_pct).
API: `GET /api/geo/ingest/resources/{cca2}`.

`geo_ingest_sources` is seeded at startup from `backend/app/ingest/registry.py` (6 sources:
`usgs_mcs` and `eia_international` active; BGS, OPEC, EI, WMD registered as inactive stubs).
Last-run metadata (`last_run_id`, `last_fetched_at`, `last_data_date`) stamped after each run.

`geo_ingest_log` records every run: status, counts, data_date, source_url, error, summary, details.

No GSIs yet — all reads are full scans. Add GSIs if collections grow past ~1 000 items.

## Ports

| Service | Internal | External (local) |
|---|---|---|
| FastAPI backend | 8000 | 8004 |
| React/Vite frontend | 4203 | 4203 |
| LocalStack | 4566 | 4570 |
| DynamoDB Admin UI | 8001 | 8005 |

## AWS deployment architecture

Lambda (in a dedicated VPC) + API Gateway + private S3 on one HTTPS origin, ~$18/month
(~$8 WAF, ~$7 Secrets Manager endpoint), IP-restricted.
CDK stack: `infra/mindmap_geo_lambda_stack.py`.

```
Browser ──HTTPS (TLS 1.2+)──> exploror.labs.pasadena.ai
                              API Gateway REST API (Regional custom domain, ACM cert, WAF, IP allowlist)
  ├─ GET /, /{proxy+}    →  S3 service integration (private bucket, GetObject-only IAM role)
  ├─ ANY /api/{proxy+}   →  Lambda (FastAPI + Mangum, arm64, 512MB, 30s timeout)
  └─ GET /health         →  Lambda
                                   ↓  (dedicated VPC, isolated subnets, no IGW/NAT)
                              DynamoDB gateway endpoint (policy: v2_* tables)
                              Secrets Manager interface endpoint (policy: one secret)
```

**Network:** the API Lambda runs in private-isolated subnets of a dedicated VPC
(`10.60.0.0/24`, 2 AZs, `pai-mindmap-geo-v2-vpc`) with no internet gateway and no NAT.
It reaches DynamoDB through a gateway endpoint and Secrets Manager through an interface endpoint
(one AZ, reachable from both); each endpoint policy pins it to this stack's own resources.
VPC Flow Logs go to `/aws/vpc/pai-mindmap-geo-v2-flow`. The default VPC is not used: its subnets
are public and shared, and the playbook standard is one VPC per project.

**Consequence — ingest cannot run from this Lambda.** `POST /api/geo/ingest/run/{source_id}`
(EIA, USGS, hazard adapters) needs the public internet and will time out. Run ingest locally and
push with `scripts/sync_to_aws.py --aws-prefix v2_` until an ingest worker is split out
(FEDRAMP_GAP_ANALYSIS.md P-3/P-4).

**Why API Gateway fronts S3 instead of CloudFront or an S3 website:** the S3 website endpoint is
HTTP-only (login would travel in cleartext, SC-8), and CloudFront is not offered inside the
GovCloud partition. API Gateway REST + ACM + WAF + S3 service integration exist in both
partitions, so the same stack moves to GovCloud by changing account/region/partition config.
Trade-offs: 10 MB payload cap (assets total 6.4 MB, largest file ~180 KB), no edge caching,
`binary_media_types=["*/*"]` (API Gateway chooses binary/text from the first `Accept` type, so a
short allow-list would corrupt PNGs).

DNS is **not** managed by CDK: the `pasadena.ai` zone lives in a separate AWS account. The cert is
issued in the app account and DNS-validated by a CNAME created in the DNS account; the site
hostname is a CNAME to the stack's `RegionalDomainName` output.

### Seeding DynamoDB on first deploy (or after table wipe)

The seed scripts in `scripts/` default to LocalStack — run this inline seeder against real AWS instead:

```bash
# Requires pai-geo-seed inline policy on ecsuser (already attached)
python3 - << 'EOF'
import boto3, json, pathlib
ddb = boto3.resource("dynamodb", region_name="us-east-1")
# ... see full seeder in session history 2026-05-16
EOF
```

Seed order matters:
1. `geo_countries` — base records (250 countries from restcountries.com)
2. Globe geometry flags (`has_globe_geometry`, `globe_feature_id`) — derived from `countries-110m.json`
3. Flag paths (`flag_1x1`, `flag_4x3`) — derived from `assets/countries/flags/*/index.json`
4. `geo_elements` — run `scripts/seed_elements.py` (LocalStack only; for real AWS use the inline seeder pattern above)
5. `geo_country_elements` — run `scripts/seed_country_elements.py` (LocalStack only)
6. Ingest sources — seeded automatically on first `POST /api/geo/ingest/run/usgs_mcs`

Flag SVGs must also be uploaded to the frontend S3 bucket:
```bash
aws s3 sync assets/countries/flags s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID>/assets/countries/flags --exclude "generate_index.py"
```

Key Lambda differences vs local dev:
- `APP_ENV=aws` → lifespan skips `ensure_tables()` and `_seed_ingest_sources()`; CDK creates tables.
- `Dockerfile.lambda` uses `public.ecr.aws/lambda/python:3.12` (arm64); `requirements.aws.txt` excludes openpyxl.
- `VITE_API_URL` is left unset in AWS builds: site and API share one origin, so the app calls relative `/api` (`frontend/src/api.js`).
- No `DYNAMODB_ENDPOINT_URL` env var → aioboto3 uses real AWS DynamoDB.
- `SECRETS_BACKEND=aws`: `SECRET_KEY` (JWT signing, generated by Secrets Manager) and `EIA_API_KEY` are read at cold start from secret `pai-mindmap-geo-v2/app`; the Lambda role has `secretsmanager:GetSecretValue` on that one ARN only.

## Data sync (local ↔ AWS)

### Local persistence between container restarts

`docker-compose.local.yaml` persists LocalStack data via two mechanisms:

1. **`PERSISTENCE=1`** — tells LocalStack to write state to disk on each operation
2. **Bind mount** `./geo_localstack_data:/var/lib/localstack` — host directory survives `docker compose down`

Data survives `docker compose down && docker compose up`. Only `docker compose down -v` or
`rm -rf geo_localstack_data/state/` will wipe it (the docker-compose comment documents this).

### Syncing local → AWS (or AWS → local)

`scripts/sync_to_aws.py` — scans all 17 geo tables from one endpoint and batch-writes to the other.

```bash
# Requires AWS credentials in env or ~/.aws/credentials + pai-geo-seed IAM policy

# Push everything from LocalStack to AWS
python scripts/sync_to_aws.py

# Push specific tables only
python scripts/sync_to_aws.py --tables geo_countries geo_elements geo_country_elements

# Pull prod data down to local for debugging
python scripts/sync_to_aws.py --direction aws-to-local

# Dry run (counts only, no writes)
python scripts/sync_to_aws.py --dry-run
```

Destination tables must already exist (CDK creates them on `cdk deploy`; LocalStack creates them
at backend startup via `ensure_tables()`). Tables missing from either side are skipped with a note.

## Future integration path with mindmap-app-v3

1. Export `GlobeScene` as a lazy-loaded React component consumable by mindmap-app-v3
2. Mindmap nodes with `lat`/`lon` metadata fields map to `GeoPoint` records
3. The geo backend becomes a sidecar service in the mindmap docker-compose
4. Shared auth: mindmap JWT passes through as a Bearer token; geo backend validates
   using the same `SECRET_KEY`

## Decision log

**2026-05-09** — No auth on geo backend for v0.1. This is an internal-only service
and adding JWT now would block the prototype. Auth will be layered in during integration.

**2026-05-09** — DynamoDB-only storage (no Postgres fallback). Geo records are
schemaless enough that DynamoDB is a natural fit; Postgres overhead not justified yet.

**2026-05-09** — Geo data files moved from CDN to `public/data/`. Eliminates CDN
dependency, works in GovCloud/air-gapped deployments, and removes CORS concerns.

**2026-05-09** — Country highlight uses d3-geo canvas texture instead of earcut
triangulation. Earcut in 2D lon/lat space fails for polar countries (Canada, Russia)
because near-pole vertices span huge longitude ranges, producing bad triangles. Even
with sphere-surface subdivision, complex MultiPolygon shapes with holes (Hudson Bay)
produced artifacts. d3-geo handles poles, antimeridian splits, and holes correctly.

**2026-05-09** — Layer visibility uses Three.js `visible` prop (not conditional render)
so geometry stays in GPU memory across toggles — no re-fetch or rebuild on toggle.

**2026-05-10** — Graticule meridian hit detection uses `TubeGeometry` (not `TorusGeometry`).
A torus covering a full great circle is identical for the 0° and 180° meridians (same plane),
making them indistinguishable by raycasting. A half-great-circle tube is geometrically unique
per meridian so there is no ambiguity.

**2026-05-10** — Graticule label drag uses `setPointerCapture`, not `window.addEventListener`.
The `window` listener approach broke when invisible tube meshes were added: R3F's raycaster
competes for pointer capture on the canvas, starving the `window` listener mid-drag. Pointer
capture routes all subsequent events directly to the pressed element, bypassing the canvas
entirely.

**2026-05-10** — Graticule labels live outside the rotating group; meridian hit tubes live
inside it. Latitude rings are rotationally symmetric so labels can be fixed in world space.
Meridians are not symmetric — they must rotate with the globe, so their hit meshes are
children of the rotating `GlobeMesh` group.

**2026-05-10** — Country hover/selection borders use 3D `LineSegments`, not canvas strokes.
Canvas texture borders blur when zoomed in (texture magnification). `LineSegments` are
always 1px screen-space at any zoom. Yellow fill remains on the canvas texture; only
outlines moved to geometry. The yellow fill edge is still slightly soft at extreme zoom
(canvas texture limitation, accepted as good enough for v0.1).

**2026-05-10** — Globe fly-to stores a world-space direction vector (`flyToDir`), not
lon/lat. The fly-to target must have the globe group's Y-rotation applied before storage
(`vec.applyEuler(groupRef.current.rotation)`). Storing raw `latLonToVec3` output caused
a systematic angular offset equal to the accumulated auto-rotate angle.

**2026-05-10** — `DataPanel` z-index set to 16777272 (one above drei's Html default max
of 16777271). This is the only reliable way to keep the sidebar above Html overlays such
as graticule labels and cloud region tooltips without clipping or restructuring the DOM.

**2026-05-10** — Reference meridian lines (Prime Meridian, IDL, UTC zones) are generated
purely from math in `useMemo` rather than loaded from a data file. They are simple
parametric arcs (180 `LineSegments` per meridian from lat −90→+90) so there is no
justification for a separate hook or data file. Radius 2.003 places them just above the
country borders (2.002) with no z-fighting.

**2026-05-10** — Countries drawer auto-collapses on selection via `useEffect` on
`selectedCountry`, and auto-reopens on deselect. Typing in search calls `setListOpen(true)`
directly in the `onChange` handler — no effect needed. This avoids the need for separate
"browsing" and "detail" tabs while keeping the panel compact.

**2026-05-10** — Cities data is static JSON (`public/data/cities.json`) for the same reasons
as airports: position data is static, no CRUD needed at this stage. A `geo_cities` DynamoDB
table is planned for the enrichment phase (city profiles, timezone, links). When added it
will follow the existing `geo_points` / `geo_arcs` pattern: FastAPI router + aioboto3 repo
function + auto-created table at startup. The static JSON stays as the position source;
DynamoDB holds the enrichment layer keyed by `(name, country)`.

**2026-05-10** — Airport data is static JSON (`public/data/airports.json`), not DynamoDB.
Airport records don't require CRUD — they are curated reference data (OurAirports large_airport
filtered to IATA-coded entries). Static file eliminates API round-trips, works in air-gapped
deployments, and matches the capitals.json pattern.

**2026-05-11** — Periodic table elements stored in DynamoDB (`geo_elements`), not static JSON.
Elements are reference data that will be enriched over time (notes, visualisation metadata, links).
`backend/data/elements.json` is the canonical seed source (all 118 elements, 17 fields each).
`scripts/seed_elements.py` reads that file and batch-writes to DynamoDB. The API exposes
`GET /api/geo/elements`, `GET /api/geo/elements/{atomic_number}`,
`GET /api/geo/elements/symbol/{symbol}`, and `PUT /api/geo/elements/{atomic_number}` for updates.
PK is `atomic_number` as a string ("1"–"118") for consistency with the rest of the codebase.
`atomic_number_int` is stored as a numeric field for sorting.

**2026-05-11** — Country-element reserve profiles stored in `geo_country_elements` (one DynamoDB
record per country, keyed by `cca2`). Each record holds an `elements` list — not one record per
(country, element) pair — because the query pattern is always "all elements for this country at
once." The `data_type` field distinguishes confirmed geological reserves from production-share
figures (used for elements like Ga, Ge where reserves data is unreliable). Reserve units are
stored as compact string keys (e.g. "mt_reo") and expanded to display labels on the frontend.
Data sourced primarily from USGS Mineral Commodity Summaries 2024.

**2026-05-14** — External data ingestion pipeline added (`geo_ingest_sources`, `geo_ingest_log`,
`geo_country_resources` tables; `backend/app/ingest/` package; `GET/POST /api/geo/ingest/*`).
Two active ingestors: `usgs_mcs` and `eia_international`. Four sources registered as inactive
stubs (BGS, OPEC, EI Statistical Review, World Mining Data) — their automated ingestion requires
either a headless browser (BGS) or a manual download step and will be enabled as format parsers
are built. Ingestion runs are triggered manually via `POST /api/geo/ingest/run/{source_id}` and
execute as FastAPI background tasks; the trigger endpoint returns immediately with `run_id` and
a `poll_url`. Each run is logged with full provenance: counts, data_date, source_url, error.

**2026-05-14** — USGS MCS ingestor uses USGS ScienceBase API, not the pubs.usgs.gov Excel.
The ScienceBase catalog (`sciencebase.gov/catalog`) publishes per-commodity `_world.csv` files
with country-level production and reserves data. Discovery is dynamic: ingestor queries ScienceBase
for the most recent MCS collection that has `_world.csv` files (MCS 2025 dropped them; MCS 2024
is therefore the current live source). ~87 commodities; 57 countries updated; 295 element entries
per run; ~6 seconds total. Each element record is stamped with `_source_id`, `_data_year`, and
`_source_url` (the direct ScienceBase file URL) for full provenance.

**2026-05-14** — EIA ingestor (`eia_international`) writes to `geo_country_resources` (separate
from `geo_country_elements`) to keep energy resources (oil, gas, coal) isolated from mineral
elements. This matches the Phase 2 scope: resources get their own drawer in CountryDetail, their
own DynamoDB table, and their own API (`GET /api/geo/ingest/resources/{cca2}`). Requires
`EIA_API_KEY` env var (free registration at eia.gov/opendata); gracefully skips if unset.

**2026-05-15** — Periodic Table overlay uses `createPortal` to `document.body` (not rendered
inline in TopNav → ResourcesMenu → PeriodicTable). Root cause: `backdrop-filter: blur(8px)` on
`.top-bar` creates a CSS containing block for `position: fixed` descendants, constraining the
overlay to the 51px header height. Portal escapes the containing block while keeping all state in
TopNav. This is the canonical fix; do not render the overlay as a descendant of any element with
a non-none backdrop-filter, transform, or will-change.

**2026-05-15** — AtomScene uses a simplified Bohr model (not quantum mechanical orbitals) for
visual clarity. Shell capacities: [2, 8, 8, 18, 18, 32, 32]. Electrons capped at 8 visible per
ring. Intended to be immediately readable, not scientifically precise. Will remain as-is for v0.1.

**2026-05-15** — Element profile panel height locked with `min-height: 640px` on both
`.pt-tab-content` and `.pt-el-wrap` (640px ≈ 7 main grid rows + f-block rows + legend).
Without this lock, switching from the Periodic Table tab to an element profile tab would shrink
the panel. The scrollable body uses `flex: 1; overflow-y: auto; min-height: 0` — the `min-height: 0`
override is required for a flex child to scroll rather than grow past its container.

**2026-05-16** — `MATERIALS_BY_SYMBOL` lookup is a static frontend-only map, not a backend table.
The materials list is curated domain knowledge unlikely to change frequently and requires no CRUD.
If materials data needs to be editable or sourced from an external DB (e.g. MatWeb, ASM), move it
to a `geo_materials` DynamoDB table with a `PUT /api/geo/materials/{symbol}` endpoint. For now,
static is correct.

**2026-05-10** — "Baseline globe" tag marks the completion of the core interactive globe:
dot land mask, country borders/hover/selection/fly-to, graticule, cloud region overlays,
reference meridians (Prime, IDL, UTC zones), and the countries detail panel. All subsequent
commits add content layers or new functionality on top of this stable base.
