# Session Handoff

## Verified Now

- What is currently working: the harness only. No product code exists.
- What verification actually ran: `./init.sh` → `scripts/check_harness.py` and its unit tests, all passing.

## Changed This Session

- Code or behavior added: none (harness setup).
- Infrastructure or harness changes: everything in Session 001 of `claude-progress.md`.

## Broken Or Unverified

- Known defect: none.
- Unverified path: `.github/workflows/ci.yml` has not run on GitHub yet; check the first PR's checks.
- Risk for the next session: m0-001 must keep `scripts/check_harness.py` and its tests inside `just check`, or the harness loses its enforcement.

## Next Best Step

- Highest-priority unfinished feature: m0-001 Go module, binary entrypoint, mise + just.
- Why it is next: every other feature depends on the toolchain and `just check`.
- What counts as passing: its four verification steps in `feature_list.json`.
- What must not change during that step: `docs/design.md`, `DECISIONS.md` answers, the feature list rules.

## Commands

- Startup: `./init.sh`
- Verification: `./scripts/verify.sh`
- Focused debug command: `python3 scripts/check_harness.py`
