# Progress Log

Read the Current Verified State at the start of every session; update it and
add a session entry before you stop. (The filename is a harness convention; any
agent uses it.)

## Current Verified State

- Repository root: repository checkout root (contains `AGENTS.md`)
- Standard startup path: `./init.sh`
- Standard verification path: `./scripts/verify.sh` (becomes `just check` after m0-001)
- Features passing: 0 / 54
- Current highest-priority unfinished feature: m0-001 Go module, binary entrypoint, mise + just
- Current blocker: none. Open human decisions D-001 to D-010 all have defaults; none blocks M0.

## Session Log

### Session 001

- Date: 2026-11-26
- Goal: Set up the repository for agent-built development from the design doc and the learn-harness-engineering templates.
- Completed: Markdown copy of the design at `docs/design.md`; root `AGENTS.md` (+ `CLAUDE.md` symlink); `init.sh` and `scripts/verify.sh`; `feature_list.json` with 54 features across M0–M4; `DECISIONS.md` with the design's open questions plus setup decisions; `docs/harness/` (operating model, ownership, evaluator rubric, quality document, clean-state checklist, module AGENTS.md template); ADR 0001; CODEOWNERS, PR and issue templates, CI workflow; `scripts/check_harness.py` with tests; SessionStart hook printing a brief.
- Verification run: `./init.sh` (runs `scripts/check_harness.py` and its unit tests).
- Evidence captured: `harness: ok`; 14 unit tests pass, including one canary per harness rule.
- Commits: initial harness commit on branch `sk/wizardly-cerf-dcesk4`.
- Files or artifacts updated: all of the above.
- Known risk or unresolved issue: CODEOWNERS is advisory until branch protection is enabled (D-010). No agent scheduling exists yet (D-009). The architecture diagram in `docs/design.md` is an ASCII redraw of the original.
- Next best step: m0-001.
