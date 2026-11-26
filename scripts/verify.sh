#!/usr/bin/env bash
# Standard verification path. CI runs exactly this.
# Once a justfile exists, `just check` is the single entry point and must
# itself call scripts/check_harness.py (feature m0-001 wires this up).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -f justfile ]; then
  if ! command -v just >/dev/null 2>&1; then
    echo "verify: justfile present but 'just' is not installed (run: mise install)" >&2
    exit 1
  fi
  exec just check
fi

echo "==> Harness integrity"
python3 scripts/check_harness.py
python3 -m unittest discover -s scripts -p 'test_*.py' -q
