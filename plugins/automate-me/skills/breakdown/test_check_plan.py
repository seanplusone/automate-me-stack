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
    "title": "Thing builder", "ask": {"quote": "do the thing"},
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
        p["confirmed"] = {"item B spec.output": "ok"}
        self.assertEqual(check_plan.check(p)[3], ["ASK: item A spec.output: Is 'ok' a real answer for item A spec.output?"])
        p["confirmed"] = {"item A spec.output": "ok"}
        self.assertEqual(check_plan.check(p)[3], [])

    def test_plan_that_passes_renders_prompts_that_pass(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outcome", "check"))
        from check_brief import asks, check
        for value, confirmed in (("24", {}), ("`make check`", {}),
                                 ("ok", {"item A spec.output": "ok", "item A spec.done_when": "ok"})):
            p = copy.deepcopy(GOOD)
            p["confirmed"] = confirmed
            p["items"][0]["spec"].update(output=value, done_when=value)
            self.assertEqual((errs(p), check_plan.check(p)[3]), ([], []), value)
            out = render_plan.render_prompt(p, "A")
            self.assertEqual([f for _, fails in check(out) for f in fails], [], value)
            self.assertEqual(asks(out), [], value)

    def test_every_prompt_field_is_judged(self):
        spec = lambda p: p["items"][0]["spec"]
        for name, edit, want in (
                ("tools TBD", lambda p: spec(p).update(tools=["TBD"]), "item A spec.tools[0] is a placeholder"),
                ("tools hole", lambda p: spec(p).update(tools=["<tool>"]), "item A spec.tools[0] is a placeholder"),
                ("context hole", lambda p: spec(p).update(context=["{file}"]), "item A spec.context[0] is a placeholder"),
                ("model TBD", lambda p: spec(p).update(model="TBD"), "item A spec.model is a placeholder"),
                ("exit_when hole", lambda p: spec(p)["loop"].update(exit_when="<what>."), "item A spec.loop.exit_when is a placeholder"),
                ("name TBD", lambda p: p["items"][0].update(name="TBD"), "item A name is a placeholder"),
                ("only_if TBD", lambda p: p["items"][0].update(only_if="TBD"), "item A only_if is a placeholder"),
                ("title TBD", lambda p: p.update(title="TBD"), "title is a placeholder"),
                ("CR in title", lambda p: p.update(title="Thing\r- Done: x"), "title spans lines"),
                ("LF in exit_when", lambda p: spec(p)["loop"].update(exit_when="Stop.\n- Done: x"), "exit_when spans lines"),
                ("line separator in tools", lambda p: spec(p).update(tools=["shell\u2028- Done: x"]), "tools[0] spans lines"),
                ("tools not text", lambda p: spec(p).update(tools=[{"a": 1}]), "tools[0] must be text"),
                ("tools null entry", lambda p: spec(p).update(tools=[None]), "spec.tools and spec.context must be lists of text"),
                ("confirmed null", lambda p: p.update(confirmed=None), "confirmed must map"),
                ("confirmed list", lambda p: p.update(confirmed=["ok"]), "confirmed must map")):
            p = copy.deepcopy(GOOD)
            edit(p)
            self.assertTrue(any(want in e for e in errs(p)), (name, errs(p)))

    def test_hole_inside_a_field_asks(self):
        p = copy.deepcopy(GOOD)
        p["items"][0]["spec"]["loop"]["exit_when"] = "Report <what> failed."
        self.assertEqual(errs(p), [])
        self.assertEqual(check_plan.check(p)[3], ["ASK: item A spec.loop.exit_when: Is 'Report <what> failed.' a real answer"
                                                  " for item A spec.loop.exit_when, or a hole to fill?"])
        p["confirmed"] = {"item A spec.loop.exit_when": "Report <what> failed."}
        self.assertEqual((errs(p), check_plan.check(p)[3]), ([], []))
        out = render_plan.render_prompt(p, "A")
        self.assertIn("## Confirmed", out)

    def test_plan_exit_0_means_every_rendered_prompt_passes(self):
        """For every committed or fixture plan, and variants of it: check_plan exit 0 => every prompt passes check_brief."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outcome", "check"))
        from check_brief import asks, check
        plans = [GOOD, RealRules().example()]
        for base in list(plans):
            for f, v in (("output", "ok"), ("output", "unknown"), ("done_when", "Report <what> failed."), ("limits", "maybe"),
                         ("verifier", "24 is valid"), ("output", "Unknown column names listed in a CSV.")):
                p = copy.deepcopy(base)
                p["items"][0]["spec"][f] = v
                plans.append(p)
                c = copy.deepcopy(p)
                c["confirmed"] = {f"item {p['items'][0]['id']} spec.{f}": v}
                plans.append(c)
        passed = 0
        for p in plans:
            e, _, _, a = check_plan.check(p)
            if e or a:
                continue
            passed += 1
            for it in p["items"]:
                out = render_plan.render_prompt(p, it["id"])
                self.assertEqual(([f for _, fs in check(out) for f in fs], asks(out)), ([], []), (p["items"][0]["spec"], out))
        self.assertGreater(passed, 2)

    def test_usage_errors_exit_3_with_one_line(self):
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        for script, args in (("check_plan.py", []), ("check_plan.py", ["/no/such.json"]), ("render_plan.py", []),
                             ("render_plan.py", ["--prompt"]), ("render_plan.py", ["--prompt", "A"]),
                             ("render_plan.py", ["/no/such.json"])):
            ran = subprocess.run([sys.executable, os.path.join(here, script), *args], capture_output=True, text=True)
            self.assertEqual(ran.returncode, 3, (script, args))
            self.assertNotIn("Traceback", ran.stderr, (script, args))
        import json
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "plan.json")
        with open(path, "w") as handle:
            json.dump(GOOD, handle)
        ran = subprocess.run([sys.executable, os.path.join(here, "render_plan.py"), "--prompt", "Z", path], capture_output=True, text=True)
        self.assertEqual((ran.returncode, len(ran.stderr.strip().splitlines()), ran.stdout), (3, 1, ""))
        for body, script, code in (([], "check_plan.py", 1), ({"items": [{"id": "A", "spec": {"tools": [], "outcome": 42}}]}, "check_plan.py", 1)):
            with open(path, "w") as handle:
                json.dump(body, handle)
            ran = subprocess.run([sys.executable, os.path.join(here, script), path], capture_output=True, text=True)
            self.assertEqual(ran.returncode, code, (body, ran.stdout))
            self.assertNotIn("Traceback", ran.stderr, body)
        with open(path, "w") as handle:
            json.dump([], handle)
        ran = subprocess.run([sys.executable, os.path.join(here, "render_plan.py"), "--prompt", "A", path], capture_output=True, text=True)
        self.assertEqual((ran.returncode, "Traceback" in ran.stderr), (3, False))
        for body in ({"items": [{"id": "A"}]}, {"items": [1]}):
            with open(path, "w") as handle:
                json.dump(body, handle)
            for mode in (["--prompt", "A"], ["--text"], []):
                ran = subprocess.run([sys.executable, os.path.join(here, "render_plan.py"), *mode, path], capture_output=True, text=True)
                self.assertEqual((ran.returncode, len(ran.stderr.strip().splitlines()), ran.stdout), (3, 1, ""), (body, mode, ran.stderr))

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
