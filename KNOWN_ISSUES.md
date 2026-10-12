# KNOWN_ISSUES.md — mindmap-geo

## [RESOLVED] Country highlight donut/artifact on large countries
**Reported:** 2026-05-09
**Symptom:** Hovering USA, Canada, Australia, Russia showed a ring (donut) or diagonal
artifact triangles instead of a solid fill.
**Root cause:** Two separate issues:
1. Earcut triangulates in flat 2D lon/lat space. Large triangles projected onto the
   sphere dip below the ocean sphere surface (radius 1.99), failing depth testing —
   producing a visible ring (only the edges stayed above the surface).
2. Near-polar countries (Canada, Russia) have vertices spanning huge longitude ranges
   at high latitudes. Earcut treats lon/lat as Euclidean, generating wildly incorrect
   triangles that extend far outside the country's actual borders.
**Fix:** Replaced earcut with d3-geo canvas texture approach. The hovered/selected
feature is rendered into a 2048×1024 equirectangular `CanvasTexture` using `geoPath`,
then mapped onto a sphere at radius 1.997. d3-geo natively handles poles, antimeridian
crossings, and polygon holes.

## [RESOLVED] Wireframe grid showing through country highlight
**Reported:** 2026-05-09
**Symptom:** Dark star/asterisk patterns visible across highlighted countries.
**Root cause:** Highlight sphere (radius 1.992) was below the wireframe grid sphere
(radius 1.995), so wireframe rendered on top.
**Fix:** Moved highlight sphere to radius 1.997 (above wireframe, below land dots).

## [RESOLVED] Graticule label drag stopped working after meridian tubes were added
**Reported:** 2026-05-10
**Symptom:** Dragging a latitude label to rotate the column had no effect after the
invisible `TubeGeometry` hit-meshes were introduced for meridian hover/click.
**Root cause:** The original drag used `window.addEventListener('pointermove', onMove)`.
Once R3F's raycaster started processing the tube meshes, the canvas claimed pointer
capture mid-drag, and the `window` listener stopped receiving consistent events.
**Fix:** Replaced `window` listeners with `e.currentTarget.setPointerCapture(e.pointerId)`
on `pointerdown`. The browser then routes all `pointermove` / `pointerup` events directly
to the pressed label element regardless of what is under the cursor, making drag immune
to the Three.js raycaster. Removed the `useEffect` + `window` listener pair entirely;
all drag state is now in a single `dragState` ref.

## [FIXED] Graticule labels and Html tooltips bleeding over opaque sidebar
**Reported:** 2026-05-10
**Symptom:** After making the DataPanel background fully opaque, graticule labels and
cloud-region hover tooltips still appeared on top of the sidebar panel.
**Root cause:** drei's `Html` component uses `zIndexRange=[16777271, 0]` by default —
far above the sidebar's original `z-index: 10`. Making the background opaque hides the
globe behind the panel but does nothing about Html overlays which paint above it.
**Fix:** Raised `DataPanel` `z-index` to `16777272` and toggle button to `16777273`
(one/two above drei's max). The opaque background now reliably occludes all Html overlays.

## [FIXED] Country selection fly-to: 30° angular offset
**Reported:** 2026-05-10
**Symptom:** Clicking a country rotated the globe toward it but stopped ~30° short of
centering the country on screen.
**Root cause:** `latLonToVec3` returns coordinates in the globe group's LOCAL space.
Auto-rotate accumulates `groupRef.current.rotation.y` over time. Storing the raw
`latLonToVec3` result as the fly-to target ignored this offset.
**Fix:** Apply `vec.applyEuler(groupRef.current.rotation)` before storing `flyToDir`
in the Zustand store, converting the local position to world space.

## [FIXED] Country hover/selection borders blurry when zoomed in
**Reported:** 2026-05-10
**Symptom:** Hover outline (yellow fill edge) and selection white border appeared fuzzy
or soft when zooming into the globe with pinch or zoom controls.
**Root cause:** Borders were painted as canvas strokes on the 2048×1024 `CanvasTexture`.
At high zoom the texture magnifies beyond native resolution, blurring the painted strokes.
**Fix:** Removed canvas strokes; replaced with `THREE.LineSegments` geometry built from
the feature's GeoJSON rings (`featureToLineGeo`). Lines are always 1px screen-space.
Yellow fill remains on the texture — its edge is still slightly soft at extreme zoom
(accepted limitation for v0.1; would require geometry fill or higher-res texture to fix).

## [FIXED] Legend toggles unresponsive after adding zoom controls
**Reported:** 2026-05-10
**Symptom:** Clicking Legend layer toggles had no effect after the zoom control panel
was added.
**Root cause:** `<Html fullscreen>` creates a fixed full-screen overlay div. Without
`style={{ pointerEvents: 'none' }}` on the `Html` component itself (not just its children),
the overlay's container intercepted all pointer events across the viewport.
**Fix:** Added `style={{ pointerEvents: 'none' }}` directly to `<Html fullscreen>`;
the button panel inside uses `pointerEvents: 'auto'` to remain interactive.

## [RESOLVED] Periodic Table overlay constrained to header height (51px)
**Reported:** 2026-05-15
**Symptom:** The `.pt-backdrop` fixed overlay rendered as a 51px-tall strip matching
the header bar height instead of filling the full viewport.
**Root cause:** CSS spec — an element with `backdrop-filter` (non-none) creates a new
containing block for `position: fixed` descendants. `.top-bar` has `backdrop-filter: blur(8px)`,
so any fixed child rendered inside it is constrained to the header's bounding box.
Confirmed via JS: `backdrop.parentElement.tagName === 'HEADER'`, `offsetHeight === 52`.
**Fix:** Used `createPortal(<div className="pt-backdrop">…</div>, document.body)` to
escape the header's containing block entirely. State (`showPT`) remains in `TopNav`;
only the rendered output is portalled. Backdrop `align-items` changed from `center` to
`flex-start` with `overflow-y: auto` and `padding: 24px 20px` to handle content taller
than the viewport. `.pt-panel` gets `flex-shrink: 0` so the flex container doesn't
shrink it.

---

## [FIXED] Seed scripts always wrote to LocalStack instead of real AWS
**Reported:** 2026-05-16
**Symptom:** After deploying to AWS, country list was empty, no flags, no cloud regions.
**Root cause:** All scripts in `scripts/` default to `http://localhost:4570` (LocalStack). Running them
without `--endpoint` still targeted LocalStack even when AWS creds were in the environment.
**Fix:** Wrote inline Python seeders using `boto3.resource("dynamodb", region_name="us-east-1")`
(no endpoint override). Required adding `pai-geo-seed` inline IAM policy
to the deployer IAM user (BatchWriteItem, PutItem, UpdateItem, GetItem, Scan on geo_* tables).
Three-step country seed order: (1) base records, (2) globe geometry flags, (3) flag paths.
Flag SVGs are now in `frontend/public/assets/` and bundled by Vite — no manual S3 sync needed.
See ARCHITECTURE.md seeding section for the full inline seeder.

## [FIXED] Flag and airline assets deleted on every S3 deploy
**Reported:** 2026-05-17
**Symptom:** `aws s3 sync dist/ s3://... --delete` wiped country flag SVGs and airline
PNGs from the bucket on every frontend deploy because they were in a root-level `assets/`
directory outside the Vite build output.
**Root cause:** Static assets lived at the project root (`assets/countries/`, `assets/airlines/`)
and were uploaded to S3 manually. Vite's `dist/` output didn't include them, so `--delete`
removed them from S3 on each sync.
**Fix:** Moved `assets/countries/` and `assets/airlines/` into `frontend/public/assets/`.
Vite copies `public/` verbatim into `dist/` on every build, so the assets are now included
automatically. The root `assets/` directory has been removed. No code changes needed — URL
paths (`/assets/countries/flags/4x3/...`, `/assets/airlines/...`) are unchanged.

## [TODO] Wire up EventBridge Scheduler for cloud data sync crons
**Noted:** 2026-05-10
**Scope:** Cloud region/AZ sync + airline active-status sync (all providers)
**Detail:** The following bulk-sync endpoints are ready and waiting for a scheduled caller:
- `POST /api/geo/airlines/sync` — airline active status
- `POST /api/geo/{provider}-regions/sync` — region list per provider (AWS, Azure, GCP, Alibaba, OCI, IBM)
- `POST /api/geo/availability-zones/sync` — AZ list across all providers

When deployed to AWS, create one EventBridge Scheduler rule per cron task (or one rule
triggering a Step Functions state machine that fans out to all providers). Suggested
cadence: **monthly**, first day of the month. Each rule should invoke a Lambda (or ECS
task) that fetches the latest data from the provider's public API / SDK and calls the
corresponding `/sync` endpoint. The `last_updated` and `status` fields on each record
are already in place to track staleness and flag planned/announced regions on the globe.

**Pre-requisites before enabling:**
- Deploy backend to ECS (mindmap-geo service)
- Create IAM role for EventBridge Scheduler with invoke permissions
- Decide Lambda vs. ECS task as the sync worker
- Implement the actual provider API fetch logic in each worker

## [TODO] Wire up EventBridge Scheduler for data sync cron
**Noted:** 2026-05-16
**Scope:** Automate periodic local→AWS sync for reference tables (geo_countries, geo_elements, etc.)
**Detail:** `scripts/sync_to_aws.py` handles one-off manual sync. For automated periodic sync,
wire up an EventBridge Scheduler rule or a simple CI step that runs the script after any seed
script update is merged to main.

---

<!-- Issue template:
## [STATUS] Short description
**Reported:** YYYY-MM-DD
**Symptom:**
**Root cause:**
**Fix attempts:**
**Resolution:**
-->

## [ATTEMPTED] Frontend served over HTTP-only S3 website endpoint (SC-8)
**Reported:** 2026-10-08 (FEDRAMP_GAP_ANALYSIS.md)
**Symptom:** Login credentials and JWTs would travel in cleartext to the S3 website endpoint.
**Fix attempted (2026-10-12):** private S3 bucket + API Gateway S3 service integration on a Regional
custom domain with ACM cert and TLS 1.2 policy; WAF on the stage. CloudFront rejected (not in GovCloud).
**Status:** in code, `cdk synth`/`diff` clean, **not deployed**; promote to FIXED only after a
user-confirmed deploy and the post-deploy checks (HTTPS 200, PNG checksum match, TLS 1.0/1.1 rejected).

## [OPEN] Google Fonts is a third-party origin
**Reported:** 2026-10-12
**Symptom:** `frontend/index.html` loads Inter from fonts.googleapis.com / fonts.gstatic.com, so the CSP
must allow them and the page makes a third-party request from inside the intended boundary.
**Next:** self-host Inter (woff2 in `frontend/public/`), drop the origins from `CSP` in
`infra/mindmap_geo_lambda_stack.py`.

## [OPEN] CDK CLI vs aws-cdk-lib version drift
**Reported:** 2026-10-12
**Symptom:** `infra/requirements.txt` allows `aws-cdk-lib>=2.130,<3`; a fresh install resolves to a
library newer than the installed CLI (2.1120.0 supports cloud-assembly schema 53; lib 2.273 emits 54)
and `cdk synth/diff/deploy` aborts with "CLI is not compatible with the CDK library".
**Workaround:** `pip install aws-cdk-lib==2.240.0` (verified), or upgrade the CLI (`npm i -g aws-cdk`).
**Next:** pin an upper bound or document a minimum CLI version.

## [OPEN] Unverified behaviours of the API Gateway S3 proxy
**Reported:** 2026-10-12
Cannot be proven by synth; check after first deploy: greedy `{proxy+}` keys containing `/` map
correctly to S3 keys; `Content-Type` and `Cache-Control` pass through; binary assets (PNG)
are byte-identical; missing keys return 404 (S3 returns 403 without ListBucket).

## [OPEN] Ingest routes cannot run from the VPC Lambda (no internet egress)
**Reported:** 2026-10-12
**Symptom (expected, not yet observed):** `POST /api/geo/ingest/run/{source_id}` for EIA, USGS and the
hazard adapters call public HTTP APIs; the API Lambda sits in isolated subnets with no NAT, so the call
times out (30 s Lambda limit).
**Why accepted:** keeping the API Lambda fully private is the SC-7 argument; a NAT is ~$33/month.
**Workaround:** run ingest locally and push with `python scripts/sync_to_aws.py --aws-prefix v2_`.
**Next:** split an ingest worker out of the API Lambda (FEDRAMP_GAP_ANALYSIS.md P-3, P-4).

## [OPEN] cdk synth needs EC2 lookups (use the deployer profile)
**Reported:** 2026-10-12
`cdk synth` for this stack does an `availability-zones` context lookup, which `ecsuser` cannot do. Use
`AWS_PROFILE=mindmap-geo-v2-deployer` (goes through the CDK lookup role). `infra/cdk.context.json` caches
the result, contains the account ID, and is git-ignored.

## [ATTEMPTED] Static assets counted against WAF rate rule and stage throttle
**Reported:** 2026-10-12 (code review)
**Symptom (predicted):** the country list renders one flag `<img>` per row (~250); with the SPA now served
through API Gateway these count toward the WAF per-IP rate rule (1000/5 min) and the stage throttle
(was 50 rps / burst 20), causing 403/429 on the countries tab.
**Fix attempted:** rate rule scoped to `/api/`; stage throttle 200 rps / burst 400; hashed bundles
immutable, other files 5 min cache. **Needs:** post-deploy confirmation (open Countries tab, no 4xx).

## [OPEN] CSP not yet exercised against the built app
**Reported:** 2026-10-12 (code review)
`script-src 'self'`, `connect-src 'self'`, `worker-src 'self' blob:` were written without running the
built Three.js app under them; local dev sends no CSP. After deploy, check the browser console for
violations and adjust `CSP` in `infra/mindmap_geo_lambda_stack.py`.

## [OPEN] ApiS3ReadRole trust policy has no confused-deputy condition
**Reported:** 2026-10-12 (code review)
`apigateway.amazonaws.com` is trusted without `aws:SourceAccount`/`aws:SourceArn`. Not applied because
the supported condition keys for the API Gateway service principal were not verified and a wrong key
would break static serving. Low impact (bucket holds only public build output).

## [ATTEMPTED] First deploy rolled back: Lambda role lacked VPC ENI permissions
**Reported:** 2026-10-12
**Symptom:** `cdk deploy` -> `AWS::Lambda::Function` CREATE_FAILED "The provided execution role does not
have permissions to call CreateNetworkInterface"; stack ended ROLLBACK_COMPLETE.
**Root cause:** CDK attaches `AWSLambdaVPCAccessExecutionRole` only to a role it creates; the stack passes its own.
**Fix attempted:** managed policy added to the role plus a regression test (fails without the fix).
**Side effect:** resources with `RemovalPolicy.RETAIN` (21 `v2_*` tables, secret `pai-mindmap-geo-v2/app`,
assets bucket, log groups) survive a failed create and block the next deploy with "already exists". They
must be deleted by an admin identity before redeploying (the deployer user has no delete rights).

## [ATTEMPTED] Failed first create leaves RETAINed orphans that block the next deploy
**Reported:** 2026-10-12
**Fix attempted:** `--context data_removal=destroy` (tables, log groups, assets bucket DESTROY; secret always
RETAIN). Default stays RETAIN. Covered by `infra/tests/test_stack.py`.
**Residual:** a failed create still leaves the secret `pai-mindmap-geo-v2/app`; delete it with
`aws secretsmanager delete-secret --secret-id pai-mindmap-geo-v2/app --force-delete-without-recovery`
(admin identity) before retrying.

## [ATTEMPTED] CSP header emitted with literal backslashes by API Gateway
**Reported:** 2026-10-12 (found in the first post-deploy check)
**Symptom:** `content-security-policy: default-src \'self\'; ...` — the `\'` escape in a static header
mapping is not interpreted, so every source expression is invalid and a browser would block scripts.
**Fix attempted:** header mapping removed; CSP injected as `<meta http-equiv>` by a build-only Vite plugin
(`frontend/vite.config.js`). Login page loads with a clean console on the live site.
**Needs user confirmation:** globe, Countries tab and DataPanel under the CSP (requires an authenticated session).

## [OPEN] HEAD requests to the site return 403
**Reported:** 2026-10-12
Only `GET` is routed for static files and `/health`, so `curl -I` and uptime monitors using HEAD get
403 "Missing Authentication Token". Browsers are unaffected. Add HEAD methods if a monitor needs them.

## [OPEN] Site has no data until the v2 tables are seeded
**Reported:** 2026-10-12
All `v2_*` tables are empty after the first deploy; `/api/geo/countries` returns an empty list. Seed with
`python scripts/sync_to_aws.py --aws-prefix v2_` (needs the LocalStack data dir from the old repo) and create a
login with `python scripts/create_user.py <username> --table v2_geo_users`.

### Update 2026-10-12 — [ATTEMPTED] tables seeded (re: "Site has no data until the v2 tables are seeded")
Seeded the `v2_*` tables from the v1 LocalStack data (copy, v1 state untouched) with
`sync_to_aws.py --aws-prefix v2_`: 250 countries, 227 cloud regions, 70 country-element and 119
country-resource rows, 6 ingest sources, 5 ingest-log rows; `geo_elements` (empty locally) seeded from
`backend/data/elements.json` (118). Counts verified with Scan COUNT and via the live API.
Still empty by design: `v2_geo_users` (create a login), points/arcs/configs, hazard tables.
Known thin data: `geo_airlines` and `geo_availability_zones` have 1 row each in the v1 source data.
`sync_to_aws.py` no longer needs `dynamodb:ListTables` (credential check uses STS).

### Update 2026-10-12 — [ATTEMPTED] CSP and throttle PARTIALLY verified in a signed-in session (re: "CSP header emitted with literal backslashes", "CSP not yet exercised", "Static assets counted against WAF rate rule")
Gene signed in at the live site. After Resources → Periodic Table → Fe, a console capture (cropped; it began
mid-log) showed no CSP violations, only a Chrome `requestAnimationFrame` 342 ms performance notice and an
input-autocomplete advisory. Gene reported the network tab looked fine ("from what I can see"). **Not yet
explicitly confirmed:** red errors above the cropped capture, the Countries tab (~250 flags, 403/429), Cloud,
and the globe interactions. Status stays ATTEMPTED until Gene confirms FIXED; the autocomplete advisory is
fixed in `Login.jsx`.

## [FIXED] Deployer lacked ecr:DescribeImages
**Reported:** 2026-10-12
**Symptom:** `aws ecr describe-images` as `mindmap-geo-v2-cdk-deployer` returned AccessDeniedException.
**Root cause:** the live managed policy was v1 (without the action); the repo template already had it.
**Fix:** policy version v2 created and set as default (2026-10-12). IAM propagation took ~15 s, during which
the call was still denied. Verified with the deployer profile.

## [ATTEMPTED] Leaked v1 EIA API key replaced in v2 only (rotation unconfirmed)
**Reported:** 2026-10-08
**Fix attempted (2026-10-12):** key obtained via eia.gov registration and merged into `pai-mindmap-geo-v2/app`
(keys `EIA_API_KEY`, `SECRET_KEY`); Lambda image republished to start fresh environments.
**Still open:** the v1 Lambda environment and v1 git history still hold the old key; treat it as burned.
**Unconfirmed:** that the key from re-registration differs from the leaked one (EIA may re-send the same key),
and whether the old key is still valid. Compare the last characters of both keys; if identical, the leak is not remediated.

