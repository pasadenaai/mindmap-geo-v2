# Changelog

## 2026-10-12 — first deployment (branch: feat/https-front-door)
- **Deployed `MindmapGeoV2Stack` to aws01 us-east-1** (CloudFormation `CREATE_COMPLETE`, 76 resources) with `data_removal=destroy`; `https://exploror.labs.pasadena.ai/` serves the SPA over TLS 1.2+.
- First attempt rolled back (Lambda role lacked VPC ENI permissions); fixed with a managed policy and regression test; retained orphans were cleaned up by an admin.
- API Gateway emitted the CSP header with literal backslashes (`\'self\'`); CSP now ships as a `<meta>` tag injected at build time (`frontend/vite.config.js`, production build only) and the header mapping was removed. Regression test added.
- Verified post-deploy: HTTPS 200, PNG byte-identical (SHA-256), correct content types, gzip, 404 for missing keys, `/health` 200 from the VPC Lambda, unauthenticated POST 401, raw S3 URL 403, default execute-api URL 403.
- Not yet verified: login, globe/Countries tab under the CSP (needs a user), WAF block behaviour, non-allow-listed IP deny, TLS 1.0/1.1 rejection by an external probe. DynamoDB tables are empty (seed with `sync_to_aws.py --aws-prefix v2_`).

## 2026-10-12 — dedicated VPC for the API Lambda (branch: feat/https-front-door)
- New VPC `pai-mindmap-geo-v2-vpc` (`10.60.0.0/24`, 2 AZs, isolated subnets, no IGW/NAT, default SG restricted); the API Lambda runs in it with a security group allowing HTTPS egress only.
- DynamoDB gateway endpoint and Secrets Manager interface endpoint (one AZ), each with an endpoint policy scoped to this stack's resources; VPC Flow Logs to `/aws/vpc/pai-mindmap-geo-v2-flow`.
- **Behaviour change:** the ingest routes (EIA, USGS, hazard adapters) can no longer reach the internet from AWS; run ingest locally and sync. Logged in KNOWN_ISSUES.
- Gap analysis: SC-5/SC-7 rows updated and a POA&M-style plan of action (P-1 … P-12) added.
- `infra/cdk.context.json` git-ignored (contains the account ID). Estimated cost ~$18/month.

## 2026-10-12 — HTTPS front door via API Gateway S3 proxy (branch: feat/https-front-door)
- Frontend moved off the HTTP-only S3 website endpoint: private bucket, served through the same API Gateway as the API (S3 service integration), so the site is HTTPS on one origin. CloudFront deliberately not used (not offered inside the GovCloud partition).
- Regional custom domain `exploror.labs.pasadena.ai` (TLS 1.2 policy) via `cert_arn` context; ACM cert issued in aws01 and DNS-validated in the DNS account; the execute-api default endpoint is disabled when a custom domain is set.
- WAF web ACL on the stage (AWS managed Common + KnownBadInputs, per-IP rate limit); IP allowlist resource policy kept.
- Lambda routes narrowed to `/api/{proxy+}` and `/health`; everything else is served from S3.
- Both buckets private (Block Public Access, TLS-only, S3-managed encryption). Assets bucket was publicly readable behind an IP deny.
- Security headers on site (API Gateway response mapping) and API (FastAPI middleware); CORS origin derived from the site domain instead of the S3 website URL; ARNs partition-aware.
- Removed unused `__API_BASE__` define from `vite.config.js`; AWS builds leave `VITE_API_URL` unset.
- New policy `_IAM_INLINE_POLICIES/mindmap-geo-v2-cdk-deployer-policy.json` (outside repo). Not deployed.
- Verified: 20 backend tests pass; `cdk synth` and `cdk diff` (via the deployer profile) succeed against the real cert ARN.

## 2026-10-11 — hazard alerts Phase 0 (branch: main)
- New `backend/app/hazards/`: normalized `HazardEvent`, `HazardAdapter` interface, USGS earthquake and GDACS parsers (pure functions; malformed records skipped, text length-bounded).
- Fixture tests (`backend/tests/test_hazards.py`, 10 new tests); fixtures are hand-written approximations to be replaced with recorded payloads.
- CDK: `v2_geo_events` (TTL), `v2_geo_alerts`, `v2_geo_alerts_archive`, `v2_geo_event_rollups` with indexes; settings and Lambda env wired. Not deployed.
- Registered `usgs_quakes` and `gdacs` as inactive ingest sources.

## 2026-10-11 — design (branch: main)
- Added `docs/HAZARD_ALERTS_DESIGN.md`: global hazard feeds → events → deterministic scoring → Strands agent (Bedrock default, Anthropic switchable) → in-app alerts for travel/supply impact. Design only; nothing implemented.
- Design decisions recorded: country-level supply, 7-day alert visibility then archive table, public audience, Bedrock us-west-1 with partition-aware config and cheapest capable model.

## 2026-10-08 — isolated v2 stack (branch: main)
- CDK stack is now `MindmapGeoV2Stack` with `v2`-named buckets, Lambda, role, API, log group, ECR repo and secret (`pai-mindmap-geo-v2/*`) and `v2_`-prefixed DynamoDB tables; verified against the live v1 stack: no name collisions.
- Lambda role's DynamoDB access scoped to this stack's `v2_*` tables in its own account/region.
- The v2 API does not create or modify the account-wide API Gateway CloudWatch role (owned by v1): `cloud_watch_role=False`, API Gateway execution logging off.
- `scripts/sync_to_aws.py --aws-prefix v2_` seeds the v2 tables; `create_user.py --table v2_geo_users` creates logins.

## 2026-10-08 — access-control hardening (branch: main)
- All state-changing requests on the data routers now require a valid access token (`require_auth`); previously only `/auth/me` did. The frontend now sends the token on every request.
- Registration closed by default (`ALLOW_REGISTRATION`); `scripts/create_user.py` creates users. Password policy 12–128 chars, must not contain the username; login no longer leaks the policy.
- Account lockout after 5 failed logins (15 min); `audit` log events for register/login/logout/refresh.
- Logout revokes refresh tokens server-side (`token_version`); refresh checks it.
- `python-jose` 3.3.0 → 3.5.0.
- Added `backend/tests` (10 tests) and `FEDRAMP_GAP_ANALYSIS.md`.

## 2026-10-08 — v2 initial import (branch: main)
Clean, history-free copy of `pasadenaai/mindmap-geo` with credential and infrastructure-identifier cleanup.
- Removed tracked `.env.local`; added `.env.local.example` and `scripts/dev_env_init.sh` (per-developer random secrets, mode 600).
- Removed all hard-coded `aws_*_access_key*="test"` literals; LocalStack clients are sent unsigned (`scripts/_local.py`, `backend/app/repositories/dynamo.py`).
- `SECRET_KEY` has no default; AWS loads `SECRET_KEY`/`EIA_API_KEY` from Secrets Manager (`pai-mindmap-geo/app`, created by CDK, least-privilege read by the Lambda role).
- CDK: account from `CDK_DEFAULT_ACCOUNT` (no IDs in repo); `allowed_ips` context now required (fail closed instead of 0.0.0.0/0).
- Added `scripts/scan_secrets.sh`, `.gitleaks.toml`, pre-commit gitleaks hook; hardened `.gitignore`.
- Docs sanitized (account ID, API ID); documented HTTP-only S3 website endpoint as a known gap (CloudFront + TLS planned).
