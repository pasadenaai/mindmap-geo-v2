# FedRAMP Moderate — Gap Analysis (mindmap-geo-v2)

**Status:** informal self-assessment of this repo's code and CDK against the NIST SP 800-53 Rev 5 Moderate baseline, as summarised in `pasadenaai/fedramp-compliance`. Not an SSP, not a 3PAO assessment, and nothing here is "FedRAMP compliant". FedRAMP authorizes a cloud service offering and its organization, not a repository.
**Scope:** code and infrastructure-as-code only. v2 has not been deployed; no live environment was assessed. Date: 2026-10-08; network/WAF rows updated 2026-10-12.

## Summary
mindmap-geo-v2 is a commercial-region prototype (Lambda + API Gateway + S3 + DynamoDB in `us-east-1`). It has sound secrets handling and least-privilege IAM, and the access-control basics (write protection, lockout, session revocation) are now in place. It does not meet the boundary, cryptography, MFA/PIV, monitoring or documentation requirements.

## Control status
Legend: ✅ addressed in code · 🟡 partial · ❌ gap · 📄 organizational/documentation (outside the repo)

| Control | Status | Evidence / gap |
|---|---|---|
| AC-2 Account management | 🟡 | Registration closed by default (`ALLOW_REGISTRATION=false`); users created with `scripts/create_user.py`. No account review/disable workflow. |
| AC-3 Access enforcement | 🟡 | `require_auth` guards every state-changing request on `/api/geo/*`, `/geo/elements`, `/geo/ingest` (`backend/tests/test_auth.py`). Reads are public unless `REQUIRE_AUTH_FOR_READS=true`. No roles: any authenticated user can write. |
| AC-6 Least privilege | 🟡 | Lambda role scoped to `geo_*` tables, one bucket, one secret. All authenticated users share one privilege level. |
| AC-7 Unsuccessful logins | ✅ | 5 failures → 15-minute lockout (configurable), stored per user in DynamoDB. |
| AC-12 Session termination | 🟡 | Logout revokes all refresh tokens server-side (`token_version`). Access tokens (15 min in AWS) are not revocable before expiry. No refresh-token rotation with reuse detection. |
| IA-2 / IA-2(1) / IA-2(12) MFA, PIV/CAC | ❌ | Password only. No MFA, no PIV/CAC (planned Keycloak FIPS design lives in the fedramp-compliance repo). |
| IA-5 Authenticator management | 🟡 | bcrypt hashing; 12–128 char minimum (NIST 800-63B length-first); password may not contain username. No breached-password check, no password history. Signing key and API keys in Secrets Manager; `SECRET_KEY` auto-generated. |
| AU-2 / AU-3 / AU-12 Audit events | 🟡 | `audit` logger records register/login/logout/refresh outcomes with user IDs. Data-change events are not audited; no request IDs; no source IP. API Gateway execution/access logging is off so v2 stays independent of the account-wide API Gateway logging role owned by v1. |
| AU-9 / AU-11 Protection and retention | 🟡 | 10-year CloudWatch retention, `RETAIN` policy. No log integrity controls, no CloudTrail or log-archive account. |
| CA-7 Continuous monitoring | ❌ | No Security Hub, Config or GuardDuty. |
| CM-2 / CM-6 Baseline, settings | 🟡 | All infrastructure in CDK; settings in code. No drift detection; synth not gated in CI. |
| CP-9 / CP-10 Backup and recovery | 🟡 | DynamoDB PITR enabled. No tested restore, no cross-region copy. |
| RA-5 Vulnerability scanning | 🟡 | Secret scanning (gitleaks + pattern scan). No SCA/SAST/container scanning. `python-jose` upgraded to 3.5.0 to clear known 3.3.0 CVEs. |
| SA-11 Developer testing | 🟡 | Auth/access-control test suite (10 tests). No coverage of the geo routes or infrastructure. |
| SC-5 DoS protection | 🟡 | API Gateway stage throttling (200 rps, burst 400, sized for the SPA's asset traffic), WAF rate-based rule on `/api/` (1000 req / 5 min / IP), AWS Shield Standard (inherited, L3/L4). Deployed 2026-10-12. Gaps: no organization-defined DoS event list, no reserved Lambda concurrency, no alarms (see P-5, P-6, P-2). |
| SC-7 Boundary protection | 🟡 | Single managed entry point (custom domain; execute-api endpoint disabled). Deny-by-default: IP allowlist resource policy. L7 inspection: regional WAF (AWS managed Common + KnownBadInputs). S3 buckets private (Block Public Access, TLS-only). API Lambda runs in a dedicated VPC's isolated subnets (no IGW, no NAT); DynamoDB reached by a gateway endpoint and Secrets Manager by an interface endpoint, both with endpoint policies scoped to this stack's resources; VPC Flow Logs on. Gaps: commercial region; Lambda egress rule is 443 to any address, bounded only by routing; interface endpoint in one AZ; WAF/API access logging and alarms off; ingest feeds cannot run from the VPC Lambda (P-3, P-4). Deployed 2026-10-12. |
| SC-8 Transmission confidentiality | 🟡 | Site and API are served only over HTTPS from one API Gateway origin (Regional custom domain, ACM cert, TLS 1.2 policy, HSTS); S3 website endpoint removed and buckets private. Deployed 2026-10-12. Not FIPS endpoints (SC-13). |
| SC-12 / SC-28 Keys, protection at rest | 🟡 | DynamoDB and S3 use AWS-owned-key encryption by default; Secrets Manager uses the AWS-managed key. No customer-managed KMS keys. |
| SC-13 FIPS cryptography | ❌ | Not using FIPS endpoints or GovCloud; JWT uses HS256 with a shared secret. |
| SI-2 Flaw remediation | 🟡 | Pinned dependencies; no automated update process. |
| SI-4 System monitoring | ❌ | No alarms or anomaly detection. |
| SI-10 Input validation | 🟡 | Pydantic validation on request bodies. Security headers (HSTS, nosniff, frame-deny, no-referrer) on site and API responses; the SPA's CSP ships as a `<meta>` tag at build time (API Gateway static header mappings cannot carry single quotes), so `frame-ancestors` relies on `X-Frame-Options`. CORS still allows all methods/headers with credentials, but is limited to the site's own origin. |
| SR (supply chain) | ❌ | No SBOM, no provenance, no dependency review. |
| PL-2, CA-2, IR-*, CP-2, AT-*, PS-*, PM-* | 📄 | No SSP, IR plan, contingency plan, training or personnel controls. Organizational, tracked in `pasadenaai/fedramp-compliance`. |

## Prioritised remediation
1. **Done in this repo:** write protection on all data routes, closed registration, 12-char passwords, lockout, server-side logout revocation, audit events for auth, `python-jose` 3.5.0, no credential literals, fail-closed IP allowlist.
2. **Next (small):** restrict CORS methods/headers; add security headers; role claim and an admin/editor split; request-ID and source-IP in audit records; customer-managed KMS key for the secret and tables; CloudTrail data events; dependency and image scanning in CI.
3. **Architecture (large):** ~~HTTPS front door + WAF~~ done in code (API Gateway + S3 service integration + ACM + WAF; no CloudFront because it is not offered inside GovCloud) — pending deploy. Remaining: GovCloud account/partition and FIPS endpoints (SC-13), OIDC/PIV via the planned auth service (IA-2(12)), Security Hub + Config (CA-7), self-hosted fonts to remove the Google Fonts third-party origin.
4. **Organizational:** SSP, IR/CP plans, training, and an agency sponsor — see the ATO roadmap in `fedramp-compliance`.

## Plan of action (POA&M-style, informal)
Informal tracker, not the FedRAMP POA&M template: no owners or dates yet. Cost figures are us-east-1 on-demand estimates (verify before committing).

| ID | Gap | Controls | Planned fix | Est. cost | Status |
|---|---|---|---|---|---|
| P-1 | Nothing is deployed, so there is no operating evidence (configs, metrics, logs, test results) | all | Deploy; run the post-deploy checks (HTTPS/TLS, WAF block, IP deny, PNG integrity, login cookie flags); capture evidence | — | Open |
| P-2 | No WAF logging, no API access logs, no alarms on WAF blocks / throttles / 5xx | SC-7, AU-2, AU-12, SI-4 | Enable WAF logging to a `aws-waf-logs-*` CloudWatch group; set `--context api_access_logs=true` (v1's account-level API Gateway role is already set); CloudWatch alarms | ~$0.50/GB ingested | Open |
| P-3 | Ingest feeds (EIA, USGS, hazard adapters) need internet egress; the API Lambda now has none | SC-7, SC-7(5) | Split an ingest worker Lambda from the API Lambda; the API Lambda stays fully private | $0 (design) | Open — **feature regression until done** |
| P-4 | Egress for the ingest worker is uncontrolled once it exists | SC-7, SC-7(5), SC-7(8) | NAT gateway (~$33/mo + $0.045/GB) in a public subnet for the worker only; domain allow-listing needs Network Firewall or an egress proxy (materially more) | $33+ / month | Open (deferred) |
| P-5 | No reserved concurrency: a flood or runaway can exhaust account concurrency and spend | SC-5 | Set `reserved_concurrent_executions` on the API Lambda | $0 | Open |
| P-6 | SC-5 needs organization-defined DoS event types stated | SC-5, PL-2 | Define in the SSP (request flooding, application-layer abuse, volumetric L3/L4 inherited from Shield Standard) | $0 | Open |
| P-7 | Secrets Manager interface endpoint in one AZ | CP-10, SC-7 | Add the second AZ to the endpoint (Lambda spans both AZs already) | +$7.30/mo | Accepted for demo |
| P-8 | Lambda security group egress is 443 to 0.0.0.0/0 (bounded by routing, not by rule) | SC-7(5) | Use the DynamoDB prefix list and the endpoint security group as destinations (needs a prefix-list lookup) | $0 | Open |
| P-9 | AWS-owned/managed keys only | SC-12, SC-28 | Customer-managed KMS keys for DynamoDB, the secret, S3, and log groups | ~$1/key/mo | Open |
| P-10 | Commercial region, no FIPS endpoints; check managed rule-group availability and API/WAF feature parity in GovCloud | SC-13, SC-7 | Partition-aware config is in place; migrate under `*.gov.pasadena.ai`, FIPS endpoints | account + effort | Open |
| P-11 | Third-party origin: Google Fonts | SC-7, SR | Self-host Inter; drop fonts.googleapis.com / fonts.gstatic.com from the CSP | $0 | Open |
| P-12 | No Security Hub / Config / GuardDuty; no CloudTrail data events or log-archive account | CA-7, SI-4, AU-9 | Enable org-level services; send logs to an archive account | varies | Open |
| P-14 | `pai-mindmap-geo-v2-agent` Lambda (a single-call search assistant, not an autonomous agent) runs OUTSIDE the VPC with internet egress to a commercial third-party API (api.anthropic.com); user search text leaves the AWS boundary | SC-7, SC-7(5), SA-9, AC-4 | Replace with Bedrock via a VPC endpoint (stays in AWS/GovCloud) or add an egress-filtering proxy; do not enable for federal data; document the interconnection | ~$7/mo (Bedrock endpoint) | Open (accepted for the commercial beta) |
| P-13 | Deployer IAM user reaches AdministratorAccess via the CDK bootstrap deploy/execution roles | AC-6, AC-2(5), IA-5 | Scope the CloudFormation execution policy (re-bootstrap) or use short-lived deploy credentials; rotate deployer keys | $0 + effort | Open |

