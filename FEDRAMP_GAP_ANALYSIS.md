# FedRAMP Moderate — Gap Analysis (mindmap-geo-v2)

**Status:** informal self-assessment of this repo's code and CDK against the NIST SP 800-53 Rev 5 Moderate baseline, as summarised in `pasadenaai/fedramp-compliance`. Not an SSP, not a 3PAO assessment, and nothing here is "FedRAMP compliant". FedRAMP authorizes a cloud service offering and its organization, not a repository.
**Scope:** code and infrastructure-as-code only. v2 has not been deployed; no live environment was assessed. Date: 2026-10-08.

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
| SC-5 DoS protection | 🟡 | API Gateway throttling (50 rps, burst 20) plus a WAF rate-based rule (1000 req / 5 min / IP). In code, not yet deployed. |
| SC-7 Boundary protection | 🟡 | IP allowlist (resource policy) + regional WAF (AWS managed Common and KnownBadInputs rule sets) in code; S3 buckets private (Block Public Access, TLS-only). Still a commercial region and Lambda is not in a VPC. Not yet deployed. |
| SC-8 Transmission confidentiality | 🟡 | Site and API are served only over HTTPS from one API Gateway origin (Regional custom domain, ACM cert, TLS 1.2 policy, HSTS); S3 website endpoint removed and buckets private. In code, not yet deployed. Not FIPS endpoints (SC-13). |
| SC-12 / SC-28 Keys, protection at rest | 🟡 | DynamoDB and S3 use AWS-owned-key encryption by default; Secrets Manager uses the AWS-managed key. No customer-managed KMS keys. |
| SC-13 FIPS cryptography | ❌ | Not using FIPS endpoints or GovCloud; JWT uses HS256 with a shared secret. |
| SI-2 Flaw remediation | 🟡 | Pinned dependencies; no automated update process. |
| SI-4 System monitoring | ❌ | No alarms or anomaly detection. |
| SI-10 Input validation | 🟡 | Pydantic validation on request bodies. Security headers (HSTS, CSP, nosniff, frame-deny, no-referrer) on site and API responses. CORS still allows all methods/headers with credentials, but is limited to the site's own origin. |
| SR (supply chain) | ❌ | No SBOM, no provenance, no dependency review. |
| PL-2, CA-2, IR-*, CP-2, AT-*, PS-*, PM-* | 📄 | No SSP, IR plan, contingency plan, training or personnel controls. Organizational, tracked in `pasadenaai/fedramp-compliance`. |

## Prioritised remediation
1. **Done in this repo:** write protection on all data routes, closed registration, 12-char passwords, lockout, server-side logout revocation, audit events for auth, `python-jose` 3.5.0, no credential literals, fail-closed IP allowlist.
2. **Next (small):** restrict CORS methods/headers; add security headers; role claim and an admin/editor split; request-ID and source-IP in audit records; customer-managed KMS key for the secret and tables; CloudTrail data events; dependency and image scanning in CI.
3. **Architecture (large):** ~~HTTPS front door + WAF~~ done in code (API Gateway + S3 service integration + ACM + WAF; no CloudFront because it is not offered inside GovCloud) — pending deploy. Remaining: GovCloud account/partition and FIPS endpoints (SC-13), OIDC/PIV via the planned auth service (IA-2(12)), Security Hub + Config (CA-7), self-hosted fonts to remove the Google Fonts third-party origin.
4. **Organizational:** SSP, IR/CP plans, training, and an agency sponsor — see the ATO roadmap in `fedramp-compliance`.
