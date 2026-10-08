# AGENTS.md — mindmap-geo-v2

Coordination contract for multiple Claude agents working in parallel. Single-agent sessions can ignore the handoff rules.

## Roles and ownership
| Agent | Owns | Must not touch |
|---|---|---|
| backend | `backend/`, `scripts/` (seed/sync) | `frontend/`, `infra/` |
| frontend | `frontend/` | `backend/`, `infra/` |
| infra | `infra/`, `docker-compose.local.yaml`, `.env.*.example/template` | application code |
| docs/security | `*.md`, `.gitleaks.toml`, `scripts/scan_secrets.sh`, `scripts/dev_env_init.sh` | application code |

## Rules for every agent
- Never write real credentials, account IDs, or IP addresses into any tracked file. Run `scripts/scan_secrets.sh` before committing.
- Never commit `.env.local` / `.env.aws`. Secrets live in git-ignored env files (local) or Secrets Manager (AWS).
- Do not deploy or modify AWS resources without an explicit instruction from Gene.

## Handoff
- Finish with: tests/build passing, `scripts/scan_secrets.sh` clean, and a CHANGELOG.md entry.
- Record cross-boundary needs in `KNOWN_ISSUES.md` (open item) rather than editing another agent's files.

## Conflicts
- If two agents need the same file, the owner in the table above decides; the other opens a note in `KNOWN_ISSUES.md`.
