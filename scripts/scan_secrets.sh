#!/usr/bin/env bash
# Secret / sensitive-data scan. Uses gitleaks when installed (preferred), and
# always runs a dependency-free pattern scan of tracked files as a backstop.
# Exit non-zero on any finding. Usage: scripts/scan_secrets.sh
set -uo pipefail
cd "$(dirname "$0")/.."
rc=0

if command -v gitleaks >/dev/null 2>&1; then
  gitleaks detect --source . --config .gitleaks.toml --no-banner || rc=1
else
  echo "note: gitleaks not installed (brew install gitleaks); running pattern scan only" >&2
fi

files() { git ls-files -co --exclude-standard -- . ':!frontend/package-lock.json' ':!*.svg' ':!scripts/scan_secrets.sh'; }
PAT='AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_|sk-[A-Za-z0-9_-]{20,}|xox[bp]-|aws_(secret_)?access_key(_id)?["'"'"' ]*[:=]["'"'"' ]*["'"'"'][^"'"'"']+["'"'"']|(api[_-]?key|secret[_-]?key|token|password)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/+_-]{20,}'
if files | xargs grep -I -n -E -i "$PAT" 2>/dev/null; then
  echo "FAIL: credential-like literal found" >&2; rc=1
fi
# 12-digit AWS account IDs and IPv4 addresses (RFC 5737 / loopback / 0.0.0.0 allowed)
if files | xargs grep -I -n -E '\b[0-9]{12}\b' 2>/dev/null | grep -v -E '000000000000'; then
  echo "FAIL: possible AWS account ID" >&2; rc=1
fi
if files | xargs grep -I -n -E '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' 2>/dev/null \
   | grep -v -E '\b(127\.0\.0\.1|0\.0\.0\.0|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.|YOUR\.IP\.HERE|1\.2\.3\.4|5\.6\.7\.8)\b' \
   | grep -v -E 'requirements|package|==|version'; then
  echo "FAIL: possible IP address" >&2; rc=1
fi
[[ $rc -eq 0 ]] && echo "secret scan: clean"
exit $rc
