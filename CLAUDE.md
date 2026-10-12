@../../pasadena-ai-playbook/CLAUDE.md

# mindmap-geo-v2

Geographic visualisation service — interactive Three.js dot-globe with a FastAPI
backend persisting geo data in DynamoDB. Intended to integrate into mindmap-app-v3.

## Quick start (local)

```bash
scripts/dev_env_init.sh   # one-time: generates a git-ignored .env.local with random secrets
docker compose --env-file .env.local -f docker-compose.local.yaml up -d --build
```

| Service | URL |
|---|---|
| Frontend (React/Vite) | http://localhost:4203 |
| Backend (FastAPI) | http://localhost:8004 |
| API docs (Swagger) | http://localhost:8004/docs |
| DynamoDB Admin | http://localhost:8005 |
| LocalStack | http://localhost:4570 |

## Stack

- **Backend:** FastAPI · Python 3.12 · aioboto3 · DynamoDB only (no Postgres)
- **Frontend:** React 18 · Vite · Zustand · Three.js · @react-three/fiber · @react-three/drei · d3-geo · topojson-client
- **Local infra:** LocalStack 3.4 (DynamoDB + S3) · aaronshaf/dynamodb-admin

## Key files

| Path | Purpose |
|---|---|
| `backend/app/main.py` | FastAPI app, lifespan, CORS |
| `backend/app/core/config.py` | Pydantic settings (all env vars) |
| `backend/app/repositories/dynamo.py` | All DynamoDB operations + `ensure_tables()` |
| `backend/app/routers/geo.py` | CRUD endpoints for points / arcs / configs |
| `frontend/src/store/index.js` | Zustand store — single source of truth for geo data |
| `frontend/src/api.js` | Thin fetch client wrapping `/api/geo/*` |
| `frontend/src/hooks/useGlobePoints.js` | TopoJSON → land-dot positions + `latLonToVec3` |
| `frontend/src/components/GlobeScene.jsx` | Three.js scene: globe, markers, arcs |
| `frontend/src/components/DataPanel.jsx` | Right-side panel: point list, add form |

## API surface

```
GET    /api/geo/points
POST   /api/geo/points
GET    /api/geo/points/:id
PATCH  /api/geo/points/:id
DELETE /api/geo/points/:id

GET    /api/geo/arcs
POST   /api/geo/arcs
PATCH  /api/geo/arcs/:id
DELETE /api/geo/arcs/:id

GET    /api/geo/configs
POST   /api/geo/configs
PATCH  /api/geo/configs/:id
DELETE /api/geo/configs/:id

GET    /health
```

**Auth:** every POST/PATCH/PUT/DELETE under `/api/geo/*` requires `Authorization: Bearer <access token>`
(`require_auth` in `backend/app/core/security.py`). Reads are public unless `REQUIRE_AUTH_FOR_READS=true`.
Registration is closed unless `ALLOW_REGISTRATION=true` (set in the local example env); create AWS users with
`python scripts/create_user.py <username>`. Run tests: `cd backend && pip install -r requirements-dev.txt && pytest tests`.
Infra assertions (private buckets, no IGW/NAT, WAF, TLS 1.2): `cd infra && pip install -r requirements.txt pytest && pytest tests`.
FedRAMP posture: see `FEDRAMP_GAP_ANALYSIS.md`.

## AWS Lambda Deployment (beta — us-east-1)

Lambda (dedicated VPC, isolated subnets, DynamoDB + Secrets Manager endpoints) + API Gateway + private S3 behind
one HTTPS custom domain (`exploror.labs.pasadena.ai`), ~$18/month (~$8 WAF, ~$7 endpoint), IP-restricted.
**The VPC Lambda has no internet egress: the ingest routes (EIA/USGS/hazard feeds) cannot run in AWS** — ingest
locally and `sync_to_aws.py --aws-prefix v2_`. CDK stack is in `infra/`. No NAT, no ALB, no Fargate, **no CloudFront**
(CloudFront is not offered inside the GovCloud partition; every construct here exists there too).

### Architecture
```
Browser ──HTTPS (TLS 1.2+)──> API Gateway, Regional custom domain + ACM cert, WAF, IP allowlist
  ├─ GET /, /{proxy+}   →  S3 service integration (PRIVATE bucket, GetObject-only role)
  ├─ ANY /api/{proxy+}  →  Lambda (FastAPI + Mangum)
  └─ GET /health        →  Lambda
                              ↓
                         DynamoDB (real AWS, us-east-1) — v2_* tables
```

### URLs (placeholders — read the real values from the CDK stack outputs)
| Resource | URL |
|---|---|
| Site + API (same origin) | https://exploror.labs.pasadena.ai/ (`/api/*` is the API) |
| Default execute-api URL | disabled when a custom domain is configured (`cert_arn` context) |

### Deploying (first time)
```bash
# 1. Create ECR repo and push image (arm64 single-arch — Lambda rejects multi-arch manifests)
aws ecr create-repository --repository-name pai-mindmap-geo-v2-backend
cd backend
docker buildx build --platform linux/arm64 --provenance=false \
  -f Dockerfile.lambda \
  -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest \
  --push .

# 2. Deploy CDK stack (find your IP first: curl https://checkip.amazonaws.com)
cd infra
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
#    cert_arn = ACM cert for the hostname (same account + us-east-1). Issued once; the DNS zone
#    lives in a different AWS account, so the validation CNAME and the final site CNAME are
#    created there by hand (CDK does not touch DNS).
cdk deploy MindmapGeoV2Stack \
  --app "python app.py" \
  --context allowed_ips=YOUR.IP.HERE/32 \
  --context cert_arn=arn:aws:acm:us-east-1:<ACCOUNT_ID>:certificate/<ID>
# Then: CNAME exploror.labs.pasadena.ai -> the RegionalDomainName stack output (DNS account).
#    First deploy only: add `--context data_removal=destroy` so a failed create cleans itself up
#    (default RETAIN leaves tables/bucket/log groups behind and the next deploy fails with
#    "already exists"). Drop the flag once the stack holds real data.

# 3. Build and upload frontend (same-origin: leave VITE_API_URL UNSET so the app calls /api)
cd ../frontend
npm ci && npm run build
aws s3 sync dist s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID> --delete --exclude "*.py" \
  --cache-control "public,max-age=300"
aws s3 cp dist s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID> --recursive --exclude "*" \
  --include "assets/*.js" --include "assets/*.css" \
  --cache-control "public,max-age=31536000,immutable"   # hashed Vite bundles only
aws s3 cp dist/index.html s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID>/index.html \
  --cache-control "no-cache" --content-type "text/html; charset=utf-8"
# Note: flags/airlines assets are in frontend/public/assets/ and bundled by Vite —
# no separate assets sync needed.

# 4. CORS_ORIGINS is derived from the site domain in the CDK stack (no manual Lambda env edit needed)

# 5. Set EIA_API_KEY (optional — needed for EIA energy data ingest). Keys live only in
#    Secrets Manager (secret `pai-mindmap-geo-v2/app`), never in Lambda env vars or git.
#    Get a free key at https://www.eia.gov/opendata/ then merge it into the secret:
CUR=$(aws --region us-east-1 secretsmanager get-secret-value --secret-id pai-mindmap-geo-v2/app --query SecretString --output text)
aws --region us-east-1 secretsmanager put-secret-value --secret-id pai-mindmap-geo-v2/app \
  --secret-string "$(echo "$CUR" | jq --arg k "$EIA_API_KEY" '.EIA_API_KEY=$k')"
# Lambda reads the secret at cold start; update the function config or wait for a new execution environment.
```

### v2 stack isolation
This repo deploys as `MindmapGeoV2Stack` and shares nothing with the original `MindmapGeoLambdaStack`:
all names carry `v2` (`pai-mindmap-geo-v2-*` buckets/function/role/secret/ECR repo) and DynamoDB tables are prefixed `v2_`.
```bash
# Seed v2 tables from LocalStack data (users are never synced)
python scripts/sync_to_aws.py --aws-prefix v2_
# Create a login (registration is closed in AWS)
python scripts/create_user.py <username> --table v2_geo_users
```

### Updating after code changes
```bash
# Backend
cd backend
docker buildx build --platform linux/arm64 --provenance=false \
  -f Dockerfile.lambda \
  -t <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest \
  --push .
aws lambda update-function-code \
  --function-name pai-mindmap-geo-v2-backend \
  --region us-east-1 \
  --image-uri <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/pai-mindmap-geo-v2-backend:latest
aws lambda wait function-updated --function-name pai-mindmap-geo-v2-backend --region us-east-1

# Frontend
cd frontend
npm run build            # VITE_API_URL unset -> same-origin /api
aws s3 sync dist s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID> --delete --exclude "*.py" \
  --cache-control "public,max-age=300"
aws s3 cp dist s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID> --recursive --exclude "*" \
  --include "assets/*.js" --include "assets/*.css" \
  --cache-control "public,max-age=31536000,immutable"   # hashed Vite bundles only
aws s3 cp dist/index.html s3://pai-mindmap-geo-v2-frontend-<ACCOUNT_ID>/index.html \
  --cache-control "no-cache" --content-type "text/html; charset=utf-8"
# Note: flags/airlines assets are in frontend/public/assets/ — bundled by Vite, no separate sync.
```

### AWS account notes
- Target account: whichever the active AWS profile resolves to (`CDK_DEFAULT_ACCOUNT`, us-east-1); no account IDs are stored in this repo
- CDK bootstrap is required once per account/region
- Deploy identity: IAM user `mindmap-geo-v2-cdk-deployer` (permissions in `infra/iam/cdk-deployer-policy.template.json`); it assumes the account's CDK bootstrap roles, so it holds no direct create rights. `ecsuser` stays app-runtime only
- `ensure_tables()` is skipped in Lambda (APP_ENV=aws) — CDK creates all 17 tables on first deploy

### DynamoDB tables (us-east-1)
All tables use on-demand billing with PITR enabled and `RemovalPolicy.RETAIN`.

| Table | Partition Key | Notes |
|---|---|---|
| `geo_points` | `point_id` | User-placed globe markers |
| `geo_arcs` | `arc_id` | User-placed globe arcs |
| `geo_configs` | `config_id` | Globe view configs |
| `geo_countries` | `cca2` | Country metadata |
| `aws_regions` | `region_id` | AWS cloud region overlays |
| `azure_regions` | `region_id` | Azure cloud region overlays |
| `gcp_regions` | `region_id` | GCP cloud region overlays |
| `alibaba_regions` | `region_id` | Alibaba Cloud region overlays |
| `oci_regions` | `region_id` | OCI region overlays |
| `ibm_regions` | `region_id` | IBM Cloud region overlays |
| `geo_availability_zones` | `az_id` | AZ-level detail |
| `geo_airlines` | `iata` | Airline reference data |
| `geo_elements` | `atomic_number` | Periodic table (all 118) |
| `geo_country_elements` | `cca2` | Mineral reserves per country |
| `geo_country_resources` | `cca2` | Energy resources per country (EIA) |
| `geo_ingest_sources` | `source_id` | External data source registry |
| `geo_ingest_log` | `run_id` | Ingestion run history |

## Session conventions

Read `KNOWN_ISSUES.md`, `ARCHITECTURE.md`, and `ENV.md` at session start.
Update all three before session end. See playbook for full protocol.
