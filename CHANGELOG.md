# Changelog

## 2026-10-11 — design (branch: main)
- Added `docs/HAZARD_ALERTS_DESIGN.md`: global hazard feeds → events → deterministic scoring → Strands agent (Bedrock default, Anthropic switchable) → in-app alerts for travel/supply impact. Design only; nothing implemented.

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
