# Task runner. `just check` is the single verification entry point: CI,
# init.sh and scripts/verify.sh all run it. List recipes with `just --list`.

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

version := `git describe --tags --always --dirty 2>/dev/null || echo dev`

# Show available recipes.
default:
    @just --list

# Run every verification step. Must stay green on main.
check: harness fmt-check build vet test

# Harness integrity: feature list, decisions, module docs (and its own tests).
harness:
    python3 scripts/check_harness.py
    python3 -m unittest discover -s scripts -p 'test_*.py' -q

# Fail if any Go file is not gofmt-formatted.
fmt-check:
    #!/usr/bin/env bash
    set -euo pipefail
    mapfile -d '' files < <({{just_executable()}} _go-files)
    [ "${#files[@]}" -eq 0 ] && exit 0
    unformatted="$(gofmt -l -- "${files[@]}")"
    if [ -n "$unformatted" ]; then echo "gofmt needed:"; echo "$unformatted"; exit 1; fi

# Format Go code in place.
fmt:
    #!/usr/bin/env bash
    set -euo pipefail
    mapfile -d '' files < <({{just_executable()}} _go-files)
    [ "${#files[@]}" -eq 0 ] && exit 0
    gofmt -w -- "${files[@]}"

# NUL-separated list of tracked and untracked (not ignored) Go files that exist.
[private]
_go-files:
    #!/usr/bin/env bash
    set -euo pipefail
    git ls-files -z --cached --others --exclude-standard -- '*.go' |
      while IFS= read -r -d '' f; do if [ -f "$f" ]; then printf '%s\0' "$f"; fi; done

# Compile everything; -o /dev/null so no binary lands in the repo.
build:
    go build -o /dev/null ./...

vet:
    go vet ./...

test:
    go test ./...

# Build the binary into bin/ with the version stamped.
build-bin:
    go build -ldflags "-X main.version={{version}}" -o bin/gumption ./cmd/gumption

# Run the binary: `just run version`.
run *args:
    go run ./cmd/gumption "$@"
