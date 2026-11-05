import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_plan  # noqa: E402
import render_plan  # noqa: E402


def item(i, after=()):
    return {
        "id": i, "name": f"Item {i}", "plain": "It does one thing.", "after": list(after), "size": "S",
        "spec": {"outcome": "A file exists.", "done_when": "The script exits 0.", "limits": "Touch only this folder.",
                 "output": "One file.", "harness": "script check",
                 "loop": {"max": 3, "exit_when": "Report what failed."}, "verifier": "A fresh agent reruns it.", "tools": ["shell"],
                 "model": "sonnet", "effort": "medium", "context": ["plan.json"]},
        "decisions": [{"choice": "Use a script.", "over": ["Do it by hand"], "because": "It can be rerun.", "label": "inferred"}],
    }


GOOD = {
    "title": "T", "ask": {"quote": "do the thing"},
    "outcome": {"outcome": "A thing exists.", "done_when": "A check passes.", "limits": "Nothing else changes."},
    "big_picture": "The thing is missing. The plan builds it.",
    "items": [item("A"), item("B", ["A"])],
    "legend": {"script": "A file that runs."},
    "patterns": {"fired": ["import"], "not_fired": ["sync"]},
    "gaps": [{"text": "Rows in may not match rows written.", "from": "rule:import", "owner": "engineer", "changes": "A"}],
}


def errs(p):
    return check_plan.check(p)[0]


class CheckPlan(unittest.TestCase):
    def setUp(self):
        self._orig = check_plan.eng_patterns
        check_plan.eng_patterns = lambda: {"import", "sync"}

    def tearDown(self):
        check_plan.eng_patterns = self._orig

    def test_good_plan_passes(self):
        self.assertEqual(errs(GOOD), [])

    def test_large_item_must_split(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["size"] = "L"
        self.assertTrue(any("must be split" in e for e in errs(p)))

    def test_after_must_name_an_earlier_item(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["after"] = ["B"]
        self.assertTrue(any("not an earlier item" in e for e in errs(p)))

    def test_unknown_harness_fails(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"]["harness"] = "vibes"
        self.assertTrue(any("harness" in e for e in errs(p)))

    def test_loop_needs_a_cap(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"]["loop"]["max"] = 50
        self.assertTrue(any("loop.max" in e for e in errs(p)))

    def test_decision_needs_label_and_rejected_option(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["decisions"][0].update(label="sure", over=[])
        self.assertEqual(len([e for e in errs(p) if "decision" in e]), 2)

    def test_spec_needs_model_effort_and_context(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"].update(model="", effort="max", context=[])
        self.assertEqual(len([e for e in errs(p) if "spec.model" in e or "spec.effort" in e or "spec.context" in e]), 3)

    def test_gap_from_unfired_rule_fails(self):
        p = copy.deepcopy(GOOD)
        p["gaps"][0]["from"] = "rule:sync"
        self.assertTrue(any("gap 1: from" in e for e in errs(p)))

    def test_every_pattern_must_be_listed(self):
        p = copy.deepcopy(GOOD)
        p["patterns"] = {"fired": ["import"]}
        self.assertTrue(any("patterns must list" in e for e in errs(p)))

    def test_gap_must_change_an_item_or_be_a_question(self):
        p = copy.deepcopy(GOOD)
        p["gaps"][0]["changes"] = "nothing"
        self.assertTrue(any("changes must name" in e for e in errs(p)))

    def test_too_many_items_fails(self):
        p = copy.deepcopy(GOOD)
        p["items"] = [item(c) for c in "ABCDEFGHI"]
        self.assertTrue(any("limit 8" in e for e in errs(p)))


class RenderPlan(unittest.TestCase):
    def test_prompt_has_brief_check_slots_and_upstream_output(self):
        out = render_plan.render_prompt(GOOD, "B")
        for slot in ("Never say done", "Review:", "Context:", "Run on:", "not proof", "RESUME.md", "Goal:", "Check:", "Limits:", "Output:", "Verify:", "If stuck:", "Uses the output of:"):
            self.assertIn(slot, out)

    def test_page_draws_every_item(self):
        page = render_plan.render(GOOD)
        self.assertIn("<svg", page)
        self.assertEqual(page.count("<rect"), 2)


if __name__ == "__main__":
    unittest.main()
