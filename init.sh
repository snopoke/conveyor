#!/usr/bin/env bash
# Standard startup path. Every agent session runs this first.
# It installs what the repo currently needs, then runs the standard
# verification path. A failure here means the baseline is broken: fix it first.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "==> Working directory: $PWD"
echo "==> Branch: $(git branch --show-current 2>/dev/null || true)"

echo "==> Syncing dependencies"
# Each step activates once the matching part of the repo exists (built during M0).
if [ -f mise.toml ]; then
  if ! command -v mise >/dev/null 2>&1; then
    echo "init: mise is required (https://mise.jdx.dev/getting-started.html)" >&2
    exit 1
  fi
  mise trust --quiet mise.toml
  mise install
  # Put the pinned tools first on PATH for this script and everything it runs.
  mise_env="$(mise env --shell bash)"
  eval "$mise_env"
fi
if [ -f go.mod ]; then go mod download; fi
if [ -f web/package-lock.json ]; then (cd web && npm ci --no-audit --no-fund); fi
if [ -f sdk/python/pyproject.toml ] && command -v uv >/dev/null 2>&1; then (cd sdk/python && uv sync); fi

echo "==> Running baseline verification"
./scripts/verify.sh

echo "==> Start command"
if [ -f go.mod ] && [ -d cmd/gumption ]; then
  # Switch to `serve` once the binary has a server (it only has `version` today).
  START_CMD=(go run ./cmd/gumption version)
else
  START_CMD=(true)
  echo "    (no runnable app yet: see feature m0-001 in feature_list.json)"
fi
printf '    %q' "${START_CMD[@]}"; printf '\n'

if [ "${RUN_START_COMMAND:-0}" = "1" ]; then
  echo "==> Starting the app"
  exec "${START_CMD[@]}"
fi
echo "Set RUN_START_COMMAND=1 to have init.sh launch the app."
