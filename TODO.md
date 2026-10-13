# TODO — mindmap-geo-v2 (consumed at the start of the next session)

Written 2026-10-12 at the end of the PR-review / credential-hygiene session. State: **live** at
https://exploror.labs.pasadena.ai/ (aws01 us-east-1, stack `MindmapGeoV2Stack`), IP-restricted.
PR #1 was **merged** 2026-10-12 (Gene deferred his own full review; blocks 1-5 were walked by Claude).
Work top to bottom. Tick items off and move finished ones to CHANGELOG.md; never delete a KNOWN_ISSUES entry.
Never write full account IDs, IPs or key material into this repo (`scripts/scan_secrets.sh` fails CI on them).

## Where we left off (read this first)
- **Do section 0 (verify) before anything else.** The old ecsuser key is Inactive; consumers I could not see may fail.
- **Verified live:** signed-in app clean under the CSP, no 403/429; frontend with the autocomplete fix deployed;
  tables, log groups and the assets bucket are RETAIN in AWS (redeployed without `data_removal=destroy`).
- **IAM:** deployer policy is v3 (adds `ecr:DescribeImages`, drops `acm:DeleteCertificate`); the repo template and
  the `_IAM_INLINE_POLICIES/` copy match the live policy.
- **Walkthrough of PR #1:** block 1 (stack) and block 2 (tests + IAM template) done. **Blocks 3-5 still to review:**
  3 runtime code (`backend/app/main.py`, `frontend/vite.config.js`, `Login.jsx`, `scripts/*`), 4 CI/housekeeping
  (`.github/workflows/ci.yml`, `.gitignore`, `.claude/commands/*`), 5 docs accuracy.
  Decisions already made (ARCHITECTURE.md): keep the S3 403/404 -> 404 masking; no SPA fallback; data persistence first.

## 0. VERIFY FIRST in the next session  *(do before anything else; the old ecsuser key was deactivated 2026-10-12 14:14)*
The aws01 ecsuser key ending `...AD4B` was set **Inactive** on 2026-10-12 (reversible); the new key `...PXEM` is Active.
Anything that still used the old key now fails with `InvalidClientTokenId`. Confirm nothing broke:
- [ ] **This machine:** `aws --profile default sts get-caller-identity` and `--profile bedrock-dev` both succeed
      (they were verified at deactivation time). `pasadenaai-aws01` is expected to fail: it was already broken.
- [ ] **Ask Gene what has failed since:** ECS tasks / task definitions, GitHub Actions secrets, CI, the Mac mini,
      the PC, any `.env` or script that carries the old key. Look for `InvalidClientTokenId` / `UnrecognizedClient`.
- [~] **CloudTrail** (first pass 2026-10-12 ~14:30: nothing after deactivation, but only ~15 min elapsed; re-run before the delete): `aws --profile pasadenaai-aws1 --region us-east-1 cloudtrail lookup-events --lookup-attributes
      AttributeKey=AccessKeyId,AttributeValue=<OLD KEY ID>` and look for events dated after deactivation (those are
      attempts by a consumer that still holds the old key). Page through ALL results (the first check only saw the
      newest 50 events, all from this machine). The old key ID is in `~/.aws/credentials.bak-20261012`
      (`AWS_SHARED_CREDENTIALS_FILE=~/.aws/credentials.bak-20261012 aws configure get aws_access_key_id --profile default`).
- [ ] **If something broke, roll back immediately** (admin profile):
      `aws --profile pasadenaai-aws1 iam update-access-key --user-name pasadenaai_aws01_ecsuser --access-key-id <OLD KEY ID> --status Active`
      then move that consumer to the new key and deactivate again.
- [ ] **Watch period:** if nothing has failed by ~2026-10-19, delete the old key
      (`iam delete-access-key`, admin) and shred `~/.aws/credentials.bak-20261012`. Record the date in KNOWN_ISSUES.
- [ ] **Other verifications still pending from this session (nothing else has been verified for these):**
      the live `v2_geo_events` policy is still Delete (section 1); the clean spreadsheet has not been swapped in
      (section 3); the EIA key was never compared to the leaked one (section 4).

## 1. Deploy the pending retain change  *(DONE 2026-10-12: 22/22 Retain, KNOWN_ISSUES entry FIXED)*

## 2. PR #1 review and merge  *(DONE 2026-10-12; both PRs merged)*
- [ ] **Gene:** review the merged diff when time allows (post-merge); open follow-ups as new PRs.
- Optional follow-ups from block 3: generic message in the 500 handler (do not echo exception text); CI step asserting
  the CSP meta tag in `dist/index.html`; `table_exists` should report AccessDenied distinctly.

## 3. Credential rotation  *(security; in progress)*
Source: `CLAUDE_md_status_20260502.xlsx` held 7 distinct live AWS key pairs in plaintext (19 rows share them).
- [x] Clean copy built: `~/Projects/_PasadenaAI/CLAUDE_md_status_20260502_CLEAN.xlsx` (secrets removed, IDs masked, datestamped).
- [ ] **Gene:** swap the clean copy in; delete the original and the two older copies (`..._20260430.xlsx`,
      `~/Downloads/CLAUDE_md_status.xlsx`). Do not sync any of them to a cloud drive.
- [ ] **aws01 `pasadenaai_aws01_ecsuser`** (old key `...AD4B`, used by profiles `default`, `bedrock-dev`,
      `pasadenaai-aws01`): new key `...PXEM` created 2026-10-12 and written to those 3 profiles; verified via STS for
      `default` and `bedrock-dev`.
      - [x] Old key `...AD4B` deactivated 2026-10-12 14:14 (verified rejected with `InvalidClientTokenId`; new key works).
            First CloudTrail page (newest 50 events, us-east-1): all from this machine. **Verify per section 0.**
      - [ ] After the watch period (section 0), delete it (admin) and delete `~/.aws/credentials.bak-20261012` (it holds the OLD secret).
      - [ ] Update the masked IDs in the tracker (rows 3-11) to `...PXEM`.
- [x] **Six keys in other accounts** rotated 2026-10-12 (profiles `pasadenaai-aws02`, `-aws03`, `-aws04`, `-aws05`,
      `-aws06A`, `-aws07A`; each user rotated its own key, one Active key each before). New keys verified via STS and
      written to `~/.aws/credentials`; old keys set **Inactive** (reversible), not deleted. Old secrets sit in
      `~/.aws/credentials.bak-20261012-others`: shred it when the watch period ends.
      - [ ] Watch period (~2026-10-19): then `iam delete-access-key` for the six inactive keys (each account's own profile).
      - [x] **Config gotcha FIXED 2026-10-12:** removed `role_arn`/`source_profile` from the `pasadenaai-aws01`..`aws07A`
            blocks in `~/.aws/config` (backup `~/.aws/config.bak-20261012`); each profile now uses its own static key.
            `pasadenaai-aws01` is now a duplicate of `default` (delete it if unwanted).
      - [ ] **ACTION ITEM (future): provision aws13 and aws25.** Deferred by Gene 2026-10-12. Blocked on credentials
            for the Organizations management account (ID in Claude's memory file / the Organizations console, not in
            this repo): `OrganizationAccountAccessRole` trusts only that account and the aws01 admin cannot assume it.
            When available: create `pasadenaai_aws13_ecsuser` / `pasadenaai_aws25_ecsuser` with the three standard
            policies (`pai-deployer-platform`, `-data`, `-compute`, templated from aws01; no AdministratorAccess),
            write keys to the `pasadenaai-aws13` / `-aws25` profiles, record in the tracker.
            Also consider bringing `pasadenaai-aws26` (static-key user `pasadenaai_claude26`) to the ecsuser pattern.
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

## Assistant backend rollout  *(deployed and verified 2026-10-12)*
- [x] `ANTHROPIC_API_KEY` added to the `pai-mindmap-geo-v2/app` secret (Gene; verified present, no whitespace).
- [x] Image built (arm64) and pushed; `cdk diff` showed only the expected additions; `cdk deploy` UPDATE_COMPLETE.
- [x] Unauthenticated `POST /api/assistant` -> 401 with security headers; `/health` 200; 250 countries unchanged.
- [x] Frontend with the assistant fallback published (live bundle verified).
- [x] Signed-in end-to-end test (Gene, 2026-10-12): "largest country in south america" -> Brazil; no errors in CloudWatch.
- [x] Anthropic key moved to a dedicated workspace `mindmap-geo-v2` with a $10/month spend limit; old key deleted; Lambda
      recycled (`update-function-code`, same image) so it picked up the new key.
- [x] Cold start fixed: memory 512 -> 1769 MB (PR #7), init 1.1 s (was a 10 s timeout).
- [ ] Measure a signed-in warm search end to end (expect 1-3 s) after the first week of use; check Console usage by workspace.
- [ ] Consider Bedrock to stay inside the AWS boundary (FEDRAMP P-14).
- Rollback: previous API image digest is `sha256:f932d1acb14b537fc5d675ec1...` (see ECR history); to disable the feature
  without a deploy, remove `ANTHROPIC_API_KEY` from the secret (route returns 503, bar falls back to local matching).
- The API Lambda was NOT updated to the new image (it does not serve `/api/assistant`); update it on the next backend change.
## Backlog (not blocking, in rough priority)
- [x] Naming: renamed agent -> assistant (route, module, Lambda, frontend) before the first deploy, so "agent" is free for real
      agent functionality (Gene, 2026-10-12).
- [ ] Assistant bar Phase 2 (decision needed): extend actions beyond countries (Periodic Table element, DataPanel tab,
      cloud region, airline, resource layers) and/or an LLM-backed `/api/assistant` route. LLM needs: Bedrock VPC endpoint
      (~$7/mo), model access check, IAM, auth required + throttle, structured-output schema = `ACTION_TYPES`, tests.
- [x] Branch protection on `main` is ACTIVE (GitHub Pro, 2026-10-12): PR + 4 required checks, strict, no force-push/delete,
      applies to admins. See `docs/BRANCH_PROTECTION.md`.
- [ ] Branch protection follow-ups (`docs/BRANCH_PROTECTION.md`): Claude agent deny/ask rules in `.claude/settings.json`;
      weekly mirror clone + a tag per deploy; scoped fine-grained PAT.
- [ ] `pasadena-ai-playbook`: add a minimal CI check, then apply the same branch protection rule.
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
