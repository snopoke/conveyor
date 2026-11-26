#!/usr/bin/env bash
# Standard verification path. CI runs exactly this (through init.sh).
# `just check` is the single entry point and itself runs
# scripts/check_harness.py, so the harness stays enforced.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f justfile ]; then
  echo "==> just check"
  if command -v mise >/dev/null 2>&1; then
    # Use the pinned toolchain even when mise is not activated in this shell.
    exec mise exec -- just check
  fi
  if ! command -v just >/dev/null 2>&1; then
    echo "verify: justfile present but 'just' is not installed (install mise, then: mise install)" >&2
    exit 1
  fi
  exec just check
fi

echo "==> Harness integrity"
python3 scripts/check_harness.py
python3 -m unittest discover -s scripts -p 'test_*.py' -q
