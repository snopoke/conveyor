#!/usr/bin/env bash
# Prints a short brief at session start (wired as a Claude Code SessionStart
# hook in .claude/settings.json). Read-only and fast.
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 0
echo "== Gumption session brief =="
echo "Follow AGENTS.md -> Startup workflow."
sed -n '/^## Current Verified State/,/^## /p' claude-progress.md 2>/dev/null | sed '$d'
python3 - <<'PY' 2>/dev/null
import json, re
fs = json.load(open("feature_list.json"))["features"]
by = {f["id"]: f for f in fs}
open_d = set(re.findall(r"^### (D-\d{3}).*\n- \*\*Status:\*\* open", open("DECISIONS.md").read(), re.M))
prog = [f["id"] + " (" + (f["owner"] or "?") + ")" for f in fs if f["status"] == "in_progress"]
ready = [f for f in sorted(fs, key=lambda f: f["priority"]) if f["status"] == "not_started"
         and all(by[d]["status"] == "passing" for d in f["depends_on"])]
done = sum(f["status"] == "passing" for f in fs)
print(f"Features: {done}/{len(fs)} passing; in progress: {', '.join(prog) or 'none'}")
print("Next ready: " + (f"{ready[0]['id']} {ready[0]['title']}" if ready else "none"))
print(f"Open human decisions: {len(open_d)} ({', '.join(sorted(open_d))})")
PY
exit 0
