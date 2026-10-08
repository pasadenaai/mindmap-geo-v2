Wrap up the session:
1. Run `scripts/scan_secrets.sh` (must be clean) and the frontend build (`cd frontend && npm run build`).
2. Run /code-review and /security-review on the diff; fix findings.
3. Update `CHANGELOG.md` (branch, PR URL, bullets), `KNOWN_ISSUES.md`, `ARCHITECTURE.md`, `ENV.md` as needed.
4. Commit (include the Co-Authored-By trailer) and open a PR for review.
