# Protecting `main` on the free GitHub plan

**Status:** decided 2026-10-12 not to upgrade. GitHub's branch protection and rulesets are unavailable for private repos on
this plan (API: "Upgrade to GitHub Pro or make this repository public"). The "Your main branch isn't protected" banner
will therefore stay. This document lists the compensating controls. **None of them is enforced by GitHub**: a person or a
token with write access can still force-push or delete `main`. The aim is to make that hard to do by accident and easy to
notice and undo.

## What is true today (checked 2026-10-12)
- Repo is private; `pasadenaai` is the only collaborator (admin + push). No other humans can write.
- Merge methods: merge commit, squash and rebase are all allowed; auto-merge off; head branches are not auto-deleted.
- CI (4 jobs) runs on PRs and on push to `main`, but nothing requires it to pass before a merge.

## Controls, in priority order

### 1. Least privilege on whatever can push (the real control)
Any credential that can write to the repo is the "admin" of `main`.
- [ ] Settings > Collaborators: keep it at one person. Re-check with `gh api repos/pasadenaai/mindmap-geo-v2/collaborators --jq '.[].login'`.
- [ ] Use a **fine-grained PAT** per tool (Claude Code / `gh`), limited to the repos it needs, no org/admin scopes, short expiry.
      `gh auth status` shows what the current token can do. Rotate it after any session where it was exposed.
- [ ] Never put the token in CI secrets for this repo. The CI workflow already runs with `permissions: contents: read`.
- [ ] Enable 2FA (passkey) on the account and review Settings > Security log occasionally for unexpected pushes.

### 2. Stop the easy mistakes locally (client-side guard)
A hook only protects the machine it is installed on, but that is where the mistakes happen.

Create `.githooks/pre-push` (make it executable), then run `git config core.hooksPath .githooks` in each clone:
```bash
#!/usr/bin/env bash
# Refuse direct pushes to main and any non-fast-forward (force) push.
while read -r local_ref local_sha remote_ref remote_sha; do
  if [ "$remote_ref" = "refs/heads/main" ]; then
    echo "pre-push: direct push to main blocked. Open a PR." >&2; exit 1
  fi
  if [ "$remote_sha" != "0000000000000000000000000000000000000000" ] \
     && ! git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then
    echo "pre-push: non-fast-forward push to $remote_ref blocked (use --no-verify only if intended)." >&2; exit 1
  fi
done
```
Note: this also blocks the deliberate force-push to a feature branch (as in the PR #2 history scrub); use
`git push --no-verify` for those, knowingly.

### 3. Stop Claude Code from doing it (agent guard)
Add to `.claude/settings.json` so the agent must ask before the risky commands:
```json
{
  "permissions": {
    "deny": ["Bash(git push --force*)", "Bash(git push -f*)", "Bash(git push origin main*)", "Bash(git branch -D main*)"],
    "ask":  ["Bash(gh pr merge*)", "Bash(git push --force-with-lease*)"]
  }
}
```

### 4. Detect it after the fact (CI as a tripwire)
Add a job that runs on `push` to `main` and fails (visible red X, email notification) if the pushed commit did not come
from a merged PR:
```yaml
  main-came-from-pr:
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-26.04
    permissions: { contents: read, pull-requests: read }
    steps:
      - env: { GH_TOKEN: "${{ github.token }}", SHA: "${{ github.sha }}", REPO: "${{ github.repository }}" }
        run: |
          n=$(gh api "repos/$REPO/commits/$SHA/pulls" --jq 'length')
          [ "$n" -ge 1 ] || { echo "::error::commit $SHA reached main without a pull request"; exit 1; }
```
This does not prevent the push; it makes an out-of-band push loud within a minute or two.

### 5. Make it recoverable
- [ ] Keep a second copy: `git clone --mirror git@github.com:pasadenaai/mindmap-geo-v2.git` to another disk/machine and
      `git remote update` weekly (or run it from the scheduled-tasks tool).
- [ ] Tag every deploy: `git tag -a deploy-YYYYMMDD -m "..." && git push origin --tags`. A force-pushed `main` can then be
      restored with `git push --force origin <tag>:main` (the one legitimate use of a force-push).
- [ ] Record the deployed commit SHA in CHANGELOG.md (already done per deploy).

### 6. Process rules (cost nothing)
1. Every change goes through a PR; nobody pushes to `main`.
2. Merge only after `gh pr checks <n>` shows all four jobs passing. The merge is a deliberate human "go".
3. In Settings > General, set **Automatically delete head branches** on and untick merge methods you do not use
   (suggest: keep merge commit only, matching the history so far).
4. Wrap-up checklist (`.claude/commands/wrap-up.md`) already runs the secret scan and tests before the PR.

## Residual risk (accepted)
A compromised or mistaken write token can still rewrite `main`, and CI cannot block a merge. Controls 1, 4 and 5 keep
that detectable and reversible; control 2 and 3 reduce accidents. Revisit if the repo gains collaborators, goes
public, or a customer/assessor requires enforced branch protection (FedRAMP CM-3 / CM-5 evidence); at that point the
GitHub Pro (or Team) upgrade is the proper fix.
