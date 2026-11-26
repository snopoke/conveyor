"""Tests for check_harness.py: each rule has a case proving it fires.

Run: python3 -m unittest discover -s scripts -p 'test_*.py'
"""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_harness  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class CheckHarnessTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for rel in check_harness.REQUIRED_FILES:
            if rel == "CLAUDE.md":
                continue
            dst = self.tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO / rel, dst)
        (self.tmp / "CLAUDE.md").symlink_to("AGENTS.md")
        self.data = json.loads((REPO / "feature_list.json").read_text())

    def run_with(self, mutate):
        data = copy.deepcopy(self.data)
        mutate(data["features"])
        (self.tmp / "feature_list.json").write_text(json.dumps(data))
        return check_harness.check(self.tmp)

    def assertFires(self, mutate, fragment):
        errors = self.run_with(mutate)
        self.assertTrue(any(fragment in e for e in errors), f"expected {fragment!r} in {errors}")

    def test_repo_is_clean(self):
        self.assertEqual(check_harness.check(REPO), [])

    def test_passing_requires_evidence(self):
        self.assertFires(lambda fs: fs[0].update(status="passing", evidence=[]), "requires recorded evidence")

    def test_passing_requires_passing_dependencies(self):
        def m(fs):
            fs[0].update(status="not_started")
            fs[1].update(status="passing", evidence=["x"])
        self.assertFires(m, "dependency m0-001 is not")

    def test_in_progress_requires_owner(self):
        self.assertFires(lambda fs: fs[0].update(status="in_progress", owner=None), "requires an owner")

    def test_one_in_progress_per_owner(self):
        def m(fs):
            fs[0].update(status="in_progress", owner="b")
            fs[1].update(status="in_progress", owner="b")
        self.assertFires(m, "already has")

    def test_blocked_requires_notes(self):
        self.assertFires(lambda fs: fs[0].update(status="blocked", notes=""), "blocked requires notes")

    def test_unknown_dependency(self):
        self.assertFires(lambda fs: fs[0]["depends_on"].append("zz-999"), "unknown feature")

    def test_cycle(self):
        self.assertFires(lambda fs: fs[0]["depends_on"].append(fs[1]["id"]), "dependency cycle")

    def test_unknown_decision_reference(self):
        self.assertFires(lambda fs: fs[0].update(notes="waiting on D-999"), "D-999")

    def test_duplicate_id(self):
        self.assertFires(lambda fs: fs.append(copy.deepcopy(fs[0])), "duplicate id")

    def test_unknown_key(self):
        self.assertFires(lambda fs: fs[0].update(extra=1), "unknown keys")

    def test_claude_md_must_be_symlink(self):
        (self.tmp / "CLAUDE.md").unlink()
        (self.tmp / "CLAUDE.md").write_text("copy")
        self.assertIn("CLAUDE.md must be a symlink to AGENTS.md", check_harness.check(self.tmp))

    def test_module_agents_md_required_and_short(self):
        mod = self.tmp / "internal" / "domain"
        mod.mkdir(parents=True)
        self.assertTrue(any("missing AGENTS.md" in e for e in check_harness.check(self.tmp)))
        (mod / "AGENTS.md").write_text("x\n" * 151)
        self.assertTrue(any("151 lines" in e for e in check_harness.check(self.tmp)))

    def edit_decisions(self, fn):
        p = self.tmp / "DECISIONS.md"
        p.write_text(fn(p.read_text()))
        return check_harness.check(self.tmp)

    def add_open(self, entry):
        return self.edit_decisions(lambda t: t.replace("\n## Decided", f"\n{entry}\n\n## Decided", 1))

    def assertError(self, errors, fragment):
        self.assertTrue(any(fragment in e for e in errors), f"expected {fragment!r} in {errors}")

    def test_open_decision_needs_status(self):
        errors = self.add_open("### D-900 No status here\n- **Question:** ?")
        self.assertError(errors, "D-900 is under Open but lacks")

    def test_open_decision_needs_issue(self):
        errors = self.add_open("### D-901 No issue\n- **Status:** open\n- **Question:** ?")
        self.assertError(errors, "D-901 lacks a '- **Issue:**")

    def test_decided_entry_must_be_one_line(self):
        errors = self.edit_decisions(lambda t: t + "\n### D-902 Full text\n- **Status:** decided\n")
        self.assertError(errors, "decided D-902 must be a one-line entry")

    def test_decided_line_needs_issue_link(self):
        errors = self.edit_decisions(lambda t: t + "- **D-903** Something: yes.\n")
        self.assertError(errors, "malformed decided line")

    def test_decided_ids_count_as_known(self):
        line = "- **D-904** Something: yes. [#99](https://github.com/o/r/issues/99)\n"
        self.edit_decisions(lambda t: t + line)
        errors = self.run_with(lambda fs: fs[0].update(notes="see D-904"))
        self.assertFalse(any("D-904" in e for e in errors), errors)

    def test_duplicate_decision_id(self):
        errors = self.add_open("### D-001 Again\n- **Status:** open\n- **Issue:** pending")
        self.assertError(errors, "duplicate decision IDs")

    def test_progress_log_session_cap(self):
        p = self.tmp / "claude-progress.md"
        extra = "".join(f"\n### Session {900 + i}\n- Date: x\n" for i in range(6))
        p.write_text(p.read_text() + extra)
        self.assertError(check_harness.check(self.tmp), "move the oldest to docs/progress/")

    def test_evidence_item_length_cap(self):
        self.assertFires(lambda fs: fs[0]["evidence"].append("x" * 401), "evidence item of 401 chars")

    def test_evidence_item_count_cap(self):
        self.assertFires(lambda fs: fs[0]["evidence"].extend(["x"] * 16), "evidence items (max 15)")

    def archive(self, features):
        d = self.tmp / "docs" / "features"
        d.mkdir(parents=True, exist_ok=True)
        (d / "M0.json").write_text(json.dumps({"milestone": "M0", "features": features}))

    def test_archived_features_must_be_passing(self):
        f = copy.deepcopy(self.data["features"][0])
        f.update(id="zz-001", status="not_started", owner=None, depends_on=[])
        self.archive([f])
        self.assertError(check_harness.check(self.tmp), "archived feature zz-001 is not passing")

    def test_dependencies_resolve_into_archive(self):
        f = copy.deepcopy(self.data["features"][0])
        f.update(id="zz-002", status="passing", owner=None, depends_on=[], evidence=["PR #1"])
        self.archive([f])
        errors = self.run_with(lambda fs: fs[0]["depends_on"].append("zz-002"))
        self.assertFalse(any("zz-002" in e for e in errors), errors)

    def test_duplicate_id_across_archive(self):
        f = copy.deepcopy(self.data["features"][0])
        f.update(status="passing", evidence=["PR #1"])
        self.archive([f])
        self.assertError(check_harness.check(self.tmp), f"M0.json: duplicate id {f['id']}")


if __name__ == "__main__":
    unittest.main()
