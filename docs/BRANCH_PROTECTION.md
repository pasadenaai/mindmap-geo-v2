# Protecting `main`

**Status (2026-10-12):** active. The `pasadenaai` account moved to GitHub Pro, which enables branch protection on this
private repo. The rule below was applied with `gh api -X PUT repos/pasadenaai/mindmap-geo-v2/branches/main/protection`.
(Before the upgrade the free plan could not do this; the interim compensating-controls write-up is in git history,
commit `39eb1fa`.)

## The rule on `main`
| Setting | Value |
|---|---|
| Pull request required before merging | yes, **0 required approvals** (a solo owner cannot approve their own PR) |
| Required status checks | `backend-tests`, `infra-tests`, `frontend-build`, `secret-scan` |
| Branch must be up to date before merging | yes (`strict`) |
| Force pushes / branch deletion | blocked |
| Applies to admins (no bypass) | yes (`enforce_admins`) |
| Resolve conversations before merging | yes; stale approvals dismissed on new commits |

Consequences: direct pushes to `main` are rejected for everyone, including Claude Code and the repo owner; every change,
even docs-only, goes through a PR and waits for the four checks. Check the live state with:
```bash
gh api repos/pasadenaai/mindmap-geo-v2/branches/main --jq '{protected, checks: .protection.required_status_checks.contexts}'
```
Emergency bypass (deliberate, then restore): Settings > Branches > edit the rule > untick "Do not allow bypassing" /
"Include administrators", push, re-enable. Record it in KNOWN_ISSUES.

## What the rule does NOT give you (still worth doing)
Approvals are 0, so this enforces "a PR plus green CI", not a second reviewer. The remaining risk is a stolen or
over-scoped write token, or a CI check that is wrong. Controls that still apply:
- [ ] **Least privilege on write tokens:** one collaborator; fine-grained PATs scoped to the needed repos with short
      expiry; 2FA/passkey; no repo-write token in CI secrets (the workflow runs with `permissions: contents: read`).
- [ ] **Agent guard** in `.claude/settings.json`: deny `git push --force*` / `git push origin main*`, ask before `gh pr merge*`.
- [ ] **Recoverability:** a periodic `git clone --mirror` copy elsewhere, and a tag per deploy (`deploy-YYYYMMDD`).
- [ ] **Review after merge** while approvals stay at 0: Gene reviews merged diffs; open follow-ups as new PRs.

Not needed any more: the pre-push hook and the `main-came-from-pr` CI tripwire (GitHub now blocks those cases itself).

## Same rule elsewhere
`pasadenaai/pasadena-ai-playbook` has **no CI and no protection** (its PR #1 merged unreviewed). Add a minimal check
(markdown/link lint or a secret scan) and then the same rule. See TODO.md backlog.

## Revisit when
The repo gains collaborators (raise approvals to 1 and add CODEOWNERS; that may need GitHub Team) or an assessor asks
for evidence of change control (FedRAMP CM-3 / CM-5): the rule above plus PR history is that evidence.
