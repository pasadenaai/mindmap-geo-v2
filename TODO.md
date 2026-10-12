# TODO — mindmap-geo-v2 (consumed at the start of the next session)

Written 2026-10-11 at the end of the deploy session. State: **live** at https://exploror.labs.pasadena.ai/
(aws01 us-east-1, stack `MindmapGeoV2Stack`), IP-restricted to the allow-listed address. PR
[#1](https://github.com/pasadenaai/mindmap-geo-v2/pull/1) is open and **not merged**; `main` has none of this.
Work top to bottom. Tick items off and move finished ones to CHANGELOG.md; never delete a KNOWN_ISSUES entry.

## 1. Verify the signed-in app under the CSP  *(DONE 2026-10-12: Gene confirmed no red console errors, no 4xx; KNOWN_ISSUES entries marked FIXED)*
The login page was verified (clean console). Nothing behind login has been exercised yet.
- [x] Sign in at https://exploror.labs.pasadena.ai/ as `anthropic`. Open the built-in browser pane so the
      console can be read (the pane shares this machine's allow-listed IP).
- [x] Globe renders; hover/click a country; open the **Countries** tab (≈250 flag images); open Cloud,
      Resources → Periodic Table, an element profile.
- [x] `read_console_messages`: no CSP violations (`default-src 'self'`, `connect-src 'self'`,
      `worker-src 'self' blob:`, `img-src 'self' data: blob:`).
- [x] Network: no 403 (WAF) or 429 (throttle) on the Countries tab.
- [x] Fix any violation in the `CSP` constant in `frontend/vite.config.js`, rebuild, upload (see CLAUDE.md
      deploy steps), re-check. Mark the KNOWN_ISSUES CSP / throttle entries FIXED **only after Gene confirms**.
- If sign-in fails: check `v2_geo_users` (`anthropic`; hash replaced 2026-10-11, `token_version` 2) and the
  lockout fields (`failed_logins`, `locked_until`); 5 failures lock for 15 min.

## 2. Re-apply the deployer IAM policy in AWS  *(DONE 2026-10-12: policy version v2 set as default; deployer `ecr describe-images` verified after ~15 s propagation; temp file deleted)*
The repo template and local file now include `ecr:DescribeImages`; the live IAM policy does not.
- [x] `jq 'with_entries(select(.key|startswith("_")|not))' _IAM_INLINE_POLICIES/mindmap-geo-v2-cdk-deployer-policy.json > /tmp/p.json`
- [x] `aws --profile pasadenaai-aws1 iam create-policy-version --policy-arn arn:aws:iam::<ACCOUNT_ID>:policy/mindmap-geo-v2-cdk-deployer --policy-document file:///tmp/p.json --set-as-default`
- [x] Verify: `aws --profile mindmap-geo-v2-deployer ecr describe-images --repository-name pai-mindmap-geo-v2-backend --region us-east-1`
- [x] Delete `/tmp/p.json`.
- Do not use an admin profile unless Gene says so for that step.

## 3. Rotate the leaked v1 EIA API key  *(security, outstanding since 2026-10-08)*
The key is in the v1 repo's git history and in the live v1 Lambda environment.
- [x] Re-register at the provider (eia.gov/opendata) — Gene (2026-10-12). **Unconfirmed that the key differs from the leaked one.**
- [x] v2 (done 2026-10-12; secret has EIA_API_KEY + SECRET_KEY, Lambda image republished, /health 200): `aws secretsmanager put-secret-value` on `pai-mindmap-geo-v2/app` (merge into the existing JSON,
      keep `SECRET_KEY`), then force new Lambda environments (see CLAUDE.md step 5).
- [ ] v1: update the Lambda env var or remove it; consider scrubbing history or just treat the old key as burned.
- [ ] Note the rotation date in KNOWN_ISSUES.

## 4. Merge the PRs
- [ ] Only after item 1 passes and Gene confirms: merge `pasadenaai/mindmap-geo-v2#1` (review + security
      review already run; 22 backend + 11 infra tests passed; secret scan clean at last run).
- [ ] Merge `pasadenaai/pasadena-ai-playbook#1` (pattern doc + zone correction).
- [x] Redeployed **without** `--context data_removal=destroy` (done 2026-10-12, before the merge): 21 tables, 2 log
      groups and the assets bucket are RETAIN. `v2_geo_events` was still DESTROY: switched to RETAIN in code (needs one more redeploy).

## Backlog (not blocking, in rough priority)
- [ ] CI: pin GitHub Actions by commit SHA instead of tag; consider adding gitleaks and `cdk synth` once a deployer-free path exists.
- [ ] Add WAF logging + API access logs (`--context api_access_logs=true`) + alarms — POA&M P-2.
- [ ] Reserved Lambda concurrency (P-5); define SC-5 DoS event types in the SSP (P-6).
- [ ] Split an ingest worker from the API Lambda; ingest feeds cannot reach the internet from the VPC Lambda
      (P-3/P-4; routes `POST /api/geo/ingest/run/*` currently time out in AWS).
- [ ] Self-host the Inter font and drop Google Fonts from the CSP (P-11).
- [ ] Route HEAD for static files and `/health` if an uptime monitor is added (KNOWN_ISSUES).
- [ ] Untested here: WAF block behaviour, non-allow-listed IP deny, external TLS 1.0/1.1 probe.
- [ ] Airlines (1 row) and availability zones (1 row) are thin in the v1 source data.
- [ ] Pin or document the CDK CLI vs `aws-cdk-lib` version drift (`aws-cdk-lib==2.240.0` worked with CLI 2.1120.0).
- [ ] Hazard alerts Phase 1: record real USGS/GDACS payloads for fixtures (docs/HAZARD_ALERTS_DESIGN.md).
- [ ] Bedrock model access check (deployer lacks `bedrock:ListFoundationModels`).
- [ ] Tracker spreadsheet `CLAUDE_md_status_20260502.xlsx` holds plaintext IAM keys: move to a secrets store.
- [ ] Your aws profiles: `pasadenaai-aws01` (broken) vs `pasadenaai-aws1` (admin) — rename/remove the broken one.
