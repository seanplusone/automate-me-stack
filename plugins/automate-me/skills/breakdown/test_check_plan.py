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

    def test_placeholder_in_any_field_fails(self):
        for where, value in (("outcome", "TBD"), ("done_when", "To be determined."), ("limits", "<limits>"),
                             ("output", "TBD"), ("verifier", "{verifier}")):
            p = copy.deepcopy(GOOD)
            p["items"][0]["spec"][where] = value
            self.assertTrue(any(f"spec.{where} is a placeholder" in e for e in errs(p)), where)
        for where in ("outcome", "done_when", "limits"):
            p = copy.deepcopy(GOOD)
            p["outcome"][where] = "Pending."
            self.assertTrue(any(f"outcome.{where} is a placeholder" in e for e in errs(p)), where)

    def test_title_hole_and_multiline_field_fail(self):
        p = copy.deepcopy(GOOD)
        p["title"] = "<project>"
        self.assertTrue(any("title is a placeholder" in e for e in errs(p)))
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"]["output"] = "A file.\n- Goal: Ship it."
        self.assertTrue(any("spec.output spans lines" in e for e in errs(p)))

    def test_real_short_and_non_english_fields_pass(self):
        for value in ("24", "$500", "#123", "`make check`", "上线第二版。", "Запустить вторую версию."):
            p = copy.deepcopy(GOOD)
            p["items"][0]["spec"]["output"] = value
            p["items"][0]["spec"]["done_when"] = value
            self.assertEqual(errs(p), [], value)
            self.assertEqual(check_plan.check(p)[3], [], value)

    def test_needs_human_field_asks_until_confirmed(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"]["output"] = "ok"
        self.assertEqual(errs(p), [])
        self.assertEqual(check_plan.check(p)[3], ["ASK: item A spec.output: Is 'ok' a real answer for item A spec.output?"])
        p["confirmed"] = ["ok"]
        self.assertEqual(check_plan.check(p)[3], [])

    def test_plan_that_passes_renders_prompts_that_pass(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outcome", "check"))
        from check_brief import asks, check
        for value, confirmed in (("24", []), ("`make check`", []), ("ok", ["ok"])):
            p = copy.deepcopy(GOOD)
            p["confirmed"] = confirmed
            p["items"][0]["spec"].update(output=value, done_when=value)
            self.assertEqual((errs(p), check_plan.check(p)[3]), ([], []), value)
            out = render_plan.render_prompt(p, "A")
            self.assertEqual([f for _, fails in check(out) for f in fails], [], value)
            self.assertEqual(asks(out), [], value)

    def test_too_many_items_fails(self):
        p = copy.deepcopy(GOOD)
        p["items"] = [item(c) for c in "ABCDEFGHI"]
        self.assertTrue(any("limit 8" in e for e in errs(p)))


class RenderPlan(unittest.TestCase):
    def test_prompt_has_outcome_slots_and_upstream_output(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outcome", "check"))
        from check_brief import check
        out = render_plan.render_prompt(GOOD, "B")
        for slot in ("Never say done", "Review:", "Waits for:", "not proof", "RESUME.md", "- Goal:", "- Done:",
                     "- Output: One file.", "- Constraints:", "- Tools:", "- Agents and roles:", "- Evals:",
                     "- Verification:", "Uses the output of:"):
            self.assertIn(slot, out)
        self.assertNotIn("The person reads it in the reply.", out)
        self.assertNotIn("done when", out)
        self.assertNotIn("Write first:", out)
        self.assertNotIn("Report only", out)
        self.assertNotIn("the script check should pass", out)
        self.assertNotIn("harness misses", out)
        self.assertIn("unknown: What is one case that should pass", out)
        reworded = out.replace("What is one case that should pass, and one that should fail?", "Which cases prove it works?")
        self.assertEqual([f for _, fails in check(reworded) for f in fails], [])
        self.assertEqual([f for _, fails in check(out) for f in fails], [])
        quiet = copy.deepcopy(GOOD)
        quiet["items"][1]["spec"]["harness"] = "findings file"
        asked = render_plan.render_prompt(quiet, "B")
        self.assertIn("Report only", asked)
        self.assertNotIn("Review:", asked)

    def test_page_draws_every_item(self):
        page = render_plan.render(GOOD)
        self.assertIn("<svg", page)
        self.assertEqual(page.count("<rect"), 2)


class RealRules(unittest.TestCase):
    """No stub: the rule folders as they ship."""

    def example(self):
        import json
        import re
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "references", "plan-shape.md")) as handle:
            text = handle.read()
        return json.loads(re.search(r"```json\n(.*?)```", text, re.S)[1])

    def test_doc_example_passes(self):
        self.assertEqual(errs(self.example()), [])

    def test_unknown_rule_set_fails(self):
        p = self.example()
        p["gaps"][0]["from"] = "rule:no-such-set"
        self.assertTrue(any("from must be" in e for e in errs(p)))

    def test_goes_first_only_when_something_waits(self):
        p = self.example()
        self.assertNotIn("Goes first", render_plan.render(p))
        b = copy.deepcopy(p["items"][0])
        b.update(id="B", after=["A"])
        p["items"].append(b)
        self.assertIn("Goes first", render_plan.render(p))


if __name__ == "__main__":
    unittest.main()
