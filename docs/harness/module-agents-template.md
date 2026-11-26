# Module AGENTS.md template

Copy to `internal/<module>/AGENTS.md` (or `plugins/<port>/<name>/AGENTS.md`)
and fill it in. Keep it under 150 lines; `scripts/check_harness.py` enforces
this for `internal/`. An agent working in the module should need only this
file and `port.go`.

```markdown
# <module>

## Purpose
One paragraph: what this module owns (copy the "Owns" cell from
docs/design.md → Modules and boundaries, then add detail).

## Public interface
Where the port is (port.go) and the main types and functions it exposes.

## Invariants
Rules that must always hold, each with the test that proves it.
- e.g. "Merge is commutative and idempotent" → `TestMergeProperties`

## Allowed imports
Exactly the "May import" cell from docs/design.md. Enforced by .go-arch-lint.yml.

## How to test
- Unit: `go test ./internal/<module>/...`
- Integration (if any): `just test-integration -run <Pattern>`
- Coverage floor: 90% | 70%

## Gotchas
Things that surprised a previous agent. Add to this list when you get surprised.
```
