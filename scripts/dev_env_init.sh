#!/usr/bin/env bash
# Generate a per-developer .env.local (git-ignored, mode 600) from .env.local.example.
# Secrets are generated locally and never committed. Re-run with --force to rotate.
#
#   scripts/dev_env_init.sh            # create if missing
#   scripts/dev_env_init.sh --force    # regenerate (rotates SECRET_KEY)
#   EIA_API_KEY=... scripts/dev_env_init.sh --force   # also set the optional EIA key
set -euo pipefail
cd "$(dirname "$0")/.."

[[ -f .env.local.example ]] || { echo "ERROR: .env.local.example not found" >&2; exit 1; }
if [[ -f .env.local && "${1:-}" != "--force" ]]; then
  echo ".env.local already exists (use --force to regenerate)"; exit 0
fi

umask 077
rand() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-"$1"; }
tmp="$(mktemp .env.local.XXXXXX)"
trap 'rm -f "$tmp"' EXIT

while IFS= read -r line; do
  case "$line" in
    SECRET_KEY=)                   echo "SECRET_KEY=$(rand 64)" ;;
    EIA_API_KEY=)                  echo "EIA_API_KEY=${EIA_API_KEY:-}" ;;
    LOCALSTACK_ACCESS_KEY_ID=)     echo "LOCALSTACK_ACCESS_KEY_ID=$(rand 16)" ;;
    LOCALSTACK_SECRET_ACCESS_KEY=) echo "LOCALSTACK_SECRET_ACCESS_KEY=$(rand 32)" ;;
    *)                             echo "$line" ;;
  esac
done < .env.local.example > "$tmp"

mv "$tmp" .env.local && chmod 600 .env.local
trap - EXIT
echo "Wrote .env.local (mode 600). Start the stack with:"
echo "  docker compose --env-file .env.local -f docker-compose.local.yaml up -d --build"
