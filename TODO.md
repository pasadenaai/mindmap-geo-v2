# TODO — mindmap-geo-v2 (consumed at the start of the next session)

Written 2026-10-12 at the end of the PR-review / credential-hygiene session. State: **live** at
https://exploror.labs.pasadena.ai/ (aws01 us-east-1, stack `MindmapGeoV2Stack`), IP-restricted.
PR [#1](https://github.com/pasadenaai/mindmap-geo-v2/pull/1): CI green (4 jobs), mergeable, **no human review, not merged**.
Work top to bottom. Tick items off and move finished ones to CHANGELOG.md; never delete a KNOWN_ISSUES entry.
Never write full account IDs, IPs or key material into this repo (`scripts/scan_secrets.sh` fails CI on them).

## Where we left off (read this first)
- **Verified live:** signed-in app clean under the CSP, no 403/429; frontend with the autocomplete fix deployed;
  tables, log groups and the assets bucket are RETAIN in AWS (redeployed without `data_removal=destroy`).
- **IAM:** deployer policy is v3 (adds `ecr:DescribeImages`, drops `acm:DeleteCertificate`); the repo template and
  the `_IAM_INLINE_POLICIES/` copy match the live policy.
- **Walkthrough of PR #1:** block 1 (stack) and block 2 (tests + IAM template) done. **Blocks 3-5 still to review:**
  3 runtime code (`backend/app/main.py`, `frontend/vite.config.js`, `Login.jsx`, `scripts/*`), 4 CI/housekeeping
  (`.github/workflows/ci.yml`, `.gitignore`, `.claude/commands/*`), 5 docs accuracy.
  Decisions already made (ARCHITECTURE.md): keep the S3 403/404 -> 404 masking; no SPA fallback; data persistence first.

## 1. Deploy the pending retain change  *(needs Gene's explicit "deploy")*
`v2_geo_events` is still DeletionPolicy Delete in AWS; the code (commit `3255b01`) is already RETAIN. `cdk diff` showed
exactly one resource changing (Delete -> Retain, no replacement).
- [ ] Deployer profile, pinned lib: `pip install aws-cdk-lib==2.240.0` in `infra/.venv`; CDK CLI is 2.1120.0.
- [ ] `allowed_ips` = the stack output `AllowedIps`; `cert_arn` = the `aws acm list-certificates` entry for the site
      domain (the deployer can read both). **Do not pass `data_removal`.**
- [ ] `cdk diff` -> only `GeoEventsTable` Delete -> Retain; then
      `cdk deploy MindmapGeoV2Stack --app "python app.py" --context allowed_ips=... --context cert_arn=...`
- [ ] Verify: `get-template` shows 22/22 tables Retain; `/health` and `/` return 200; counts unchanged
      (250 countries, 118 elements).
- [ ] Promote the KNOWN_ISSUES entry "v2_geo_events kept DeletionPolicy DELETE" to FIXED.
- The previous retain redeploy logged 3x DELETE_FAILED on the assets bucket's auto-delete custom resource
  (cosmetic, in KNOWN_ISSUES). Cleanup may be noisy again.

## 2. Finish the PR #1 review and merge  *(gate: Gene's review + explicit go)*
- [ ] Walk blocks 3-5 (above), or Gene reviews in the GitHub UI. `gh pr checks 1` must be green.
- [ ] Merge `pasadenaai/mindmap-geo-v2#1`, then `pasadenaai/pasadena-ai-playbook#1` (pattern doc + zone correction;
      not looked at this session; it has no CI).
- Branch protection is **unavailable** on this plan (private repo, free tier), so CI is advisory.
- The loop to repeat: local checks (backend pytest, infra pytest, `npm run build`, `scripts/scan_secrets.sh`) ->
  commit -> push -> `gh pr checks` -> review -> merge -> redeploy -> verify live.

## 3. Credential rotation  *(security; in progress)*
Source: `CLAUDE_md_status_20260502.xlsx` held 7 distinct live AWS key pairs in plaintext (19 rows share them).
- [x] Clean copy built: `~/Projects/_PasadenaAI/CLAUDE_md_status_20260502_CLEAN.xlsx` (secrets removed, IDs masked, datestamped).
- [ ] **Gene:** swap the clean copy in; delete the original and the two older copies (`..._20260430.xlsx`,
      `~/Downloads/CLAUDE_md_status.xlsx`). Do not sync any of them to a cloud drive.
- [ ] **aws01 `pasadenaai_aws01_ecsuser`** (old key `...AD4B`, used by profiles `default`, `bedrock-dev`,
      `pasadenaai-aws01`): new key `...PXEM` created 2026-10-12 and written to those 3 profiles; verified via STS for
      `default` and `bedrock-dev`.
      - [ ] Deactivate the OLD key `...AD4B` (`iam update-access-key --status Inactive`; reversible). Unseen consumers
            are possible: ECS task definitions, GitHub secrets, CI, the Mac mini / PC. Watch for failures for a few days.
      - [ ] Then delete it (admin) and delete `~/.aws/credentials.bak-20261012` (it holds the OLD secret).
      - [ ] Update the masked IDs in the tracker (rows 3-11) to `...PXEM`.
- [ ] **Six keys in other accounts** (account suffixes 9731, 2804, 0173, 0435, 6432, 1473; profiles `pasadenaai-aws02`,
      `-aws03`, `-aws04`, `-aws05`, `-aws06A`, `-aws07A`): check `get-access-key-last-used` with each account's own
      profile; deactivate stale ones, rotate active ones. The aws01 admin profile cannot see them.
- [ ] Put every new key in 1Password (not a file). Longer term: SSO / short-lived credentials (POA&M P-13).
- [ ] **Gene:** delete the Claude Code transcript that contains all 7 old secrets, AFTER rotation:
      `~/Desktop/Anthropic/Claude_Code/.claude/projects/-Users-mlnotes-Projects/ae0cdf68-e6cb-4b83-9c51-531779ed5f4d.jsonl`
      (Desktop may be iCloud-synced; the content was also sent to the API, so rotation is the real remedy).
- Facts to remember: K12/K13 in the tracker are AWS OU names (false positive, not tokens). The `pasadenaai-aws01`
  profile is broken (`AssumeRole` on `OrganizationAccountAccessRole` denied for ecsuser; same with the old key). The
  ecsuser carries `pai-deployer-platform/data/compute` and `pai-geo-seed`, so it is deployer-class, not minimal.

## 4. Other open security items
- [ ] **EIA key:** Gene to compare the new key's last characters to the leaked one. If identical, the leak is NOT
      remediated. Then update or remove the old key in the v1 Lambda (needs the function name + profile); note the date.
- [ ] **Reset the `anthropic` app password** (it appeared in a screenshot on 2026-10-12):
      `python scripts/create_user.py anthropic --table v2_geo_users`; confirm it bumps `token_version`.
- [ ] **Deployer is admin-equivalent** via the CDK bootstrap roles (the cfn-exec role is AdministratorAccess).
      KNOWN_ISSUES + P-13: scope the execution policy (re-bootstrap) or use short-lived deploy credentials.
- [ ] Stop using a `default` AWS profile bound to a long-lived key.

## Backlog (not blocking, in rough priority)
- [ ] Add WAF logging + API access logs (`--context api_access_logs=true`) + alarms — POA&M P-2.
- [ ] Reserved Lambda concurrency (P-5); define SC-5 DoS event types in the SSP (P-6).
- [ ] Split an ingest worker from the API Lambda; ingest feeds cannot reach the internet from the VPC Lambda
      (P-3/P-4; routes `POST /api/geo/ingest/run/*` time out in AWS). `v2_geo_events` stays empty until then.
- [ ] CI: pin GitHub Actions by commit SHA instead of tag; consider gitleaks in CI (needs a license on org repos).
- [ ] Self-host the Inter font and drop Google Fonts from the CSP (P-11).
- [ ] Route HEAD for static files and `/health` if an uptime monitor is added (KNOWN_ISSUES).
- [ ] Untested: WAF block behaviour, non-allow-listed IP deny, external TLS 1.0/1.1 probe.
- [ ] Airlines (1 row) and availability zones (1 row) are thin in the v1 source data.
- [ ] Pin or document the CDK CLI vs `aws-cdk-lib` drift (CI pins 2.240.0; `infra/requirements.txt` is still a range).
- [ ] Hazard alerts Phase 1: record real USGS/GDACS payloads for fixtures (docs/HAZARD_ALERTS_DESIGN.md).
- [ ] Bedrock model access check (deployer lacks `bedrock:ListFoundationModels`).
- [ ] Rename/remove the broken `pasadenaai-aws01` profile (or grant the assume-role); keep `pasadenaai-aws1` (admin).
- [ ] Write the session history file ("add to history") for 2026-10-12 if not yet done.

## Admin-profile use this session (audit trail)
`pasadenaai-aws1` was used on 2026-10-12 for: IAM policy v2 and v3 creation (approved); read-only policy and exec-role
checks; `get-access-key-last-used` / `sts get-access-key-info` lookups (approved); ecsuser key creation (approved).
