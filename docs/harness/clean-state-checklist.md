# Clean state checklist

Run before ending any session. Every box must be true, or the reason it is not
must be written in `claude-progress.md`.

- [ ] `./init.sh` passes from the current tree.
- [ ] `git status` is clean apart from intended, committed changes; no stray files, debug prints, or temp canaries.
- [ ] `feature_list.json` reflects reality: nothing `passing` without evidence; your feature is `passing`, `blocked` (with notes), or still `in_progress` with a clear next step.
- [ ] `claude-progress.md` has a new session entry and an updated Current Verified State.
- [ ] `session-handoff.md` is rewritten for the next session.
- [ ] New human questions are in `DECISIONS.md` with a default.
- [ ] No half-finished step is undocumented.
- [ ] Work is committed and pushed to one PR, bookkeeping included.
- [ ] That PR is merged (agent-owned paths only, green CI, reviewer Accept), or it is ready and waiting for the human because it touches human-owned paths, or the reason it is neither is in `session-handoff.md`.
