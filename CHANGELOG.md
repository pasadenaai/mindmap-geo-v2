# Changelog

## 2026-10-08 — v2 initial import (branch: main)
Clean, history-free copy of `pasadenaai/mindmap-geo` with credential and infrastructure-identifier cleanup.
- Removed tracked `.env.local`; added `.env.local.example` and `scripts/dev_env_init.sh` (per-developer random secrets, mode 600).
- Removed all hard-coded `aws_*_access_key*="test"` literals; LocalStack clients are sent unsigned (`scripts/_local.py`, `backend/app/repositories/dynamo.py`).
- `SECRET_KEY` has no default; AWS loads `SECRET_KEY`/`EIA_API_KEY` from Secrets Manager (`pai-mindmap-geo/app`, created by CDK, least-privilege read by the Lambda role).
- CDK: account from `CDK_DEFAULT_ACCOUNT` (no IDs in repo); `allowed_ips` context now required (fail closed instead of 0.0.0.0/0).
- Added `scripts/scan_secrets.sh`, `.gitleaks.toml`, pre-commit gitleaks hook; hardened `.gitignore`.
- Docs sanitized (account ID, API ID); documented HTTP-only S3 website endpoint as a known gap (CloudFront + TLS planned).
