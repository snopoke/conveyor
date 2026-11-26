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
        self.assertFires(lambda fs: fs[0].update(status="passing"), "requires recorded evidence")

    def test_passing_requires_passing_dependencies(self):
        def m(fs):
            fs[1].update(status="passing", evidence=["x"])
        self.assertFires(m, "dependency m0-001 is not")

    def test_in_progress_requires_owner(self):
        self.assertFires(lambda fs: fs[0].update(status="in_progress"), "requires an owner")

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

    def test_decision_needs_status(self):
        p = self.tmp / "DECISIONS.md"
        p.write_text(p.read_text() + "\n### D-900 No status here\n- **Question:** ?\n")
        self.assertTrue(any("D-900 lacks" in e for e in check_harness.check(self.tmp)))

    def test_open_decision_needs_issue(self):
        p = self.tmp / "DECISIONS.md"
        p.write_text(p.read_text() + "\n### D-901 No issue\n- **Status:** open\n- **Question:** ?\n")
        self.assertTrue(any("D-901 lacks a '- **Issue:**" in e for e in check_harness.check(self.tmp)))


if __name__ == "__main__":
    unittest.main()
