"""Run: python3 check/test_map_decisions.py"""
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import check  # noqa: E402
from check_brief import ask_lines  # noqa: E402
from map_decisions import AGENTS, DECIDE, EVALS, TOOLS, main, map_text  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import check as check_decisions, main as check_decisions_main  # noqa: E402

FAILS = []
HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "..", "cases", "from-decisions")
SHAPE = os.path.join(HERE, "..", "..", "shape-idea", "cases")
SKILLS = os.path.normpath(os.path.join(HERE, "..", ".."))
ORDER = (
    "The read-back asks at most 3 questions, in this order: an open goal or done question, "
    "then the decide question, then Tools, then Agents and roles, then Evals. "
    "Unasked ones stay in Unknowns."
)
MAP = (
    "map: goal goes to Goal. done goes to Done. output goes to Output. "
    "constraints goes to Constraints. verify goes to Verification. "
    "Tools, Agents and roles, and Evals stay unknown."
)


def failed(text):
    return [name for name, items in check(text) if items]


def check_honest(name, brief):
    low = brief.lower()
    for needle in ("which tool must the run use", "who does the work", "one case that should pass"):
        if needle not in low:
            FAILS.append(f"{name} invented or dropped {needle}")
    if "write first: none" in low:
        FAILS.append(f"{name} invented write first: none")


TEXTS = []


def decisions(decided, opens="- none", parked="- none", stop="done", turns="1"):
    TEXTS.append(f"""# Decisions: sample

## Decided

{decided}
## Open

{opens}
## Parked

{parked}
## Handoff

- next: /automate-me:outcome
- stop: {stop}
- turns: {turns}
- writing: pass
- {MAP}
""")
    return TEXTS[-1]


BASE = """- goal: a tiny habit tracker on my phone
- done: mark today done in under 10 seconds
- output: the current streak on the phone
- verify: mark today once and read the streak
- constraints: no accounts, it's only me"""


def run_main(text):
    path = os.path.join(tempfile.mkdtemp(), "decisions.md")
    open(path, "w").write(text)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(path)
    return code, buf.getvalue()


def questions(brief):
    return [line[3:] for line in brief.split("## Questions", 1)[1].splitlines() if re.match(r"^\d+\. ", line)]


for name in ("done", "capped"):
    src = os.path.join(CASES, name, "decisions.md")
    brief_path = os.path.join(CASES, name, "brief.md")
    brief = map_text(open(src).read())
    want = open(brief_path).read()
    bad = failed(brief)
    if brief != want:
        FAILS.append(f"committed briefs match the mapper: {name} differs")
        print(f"FAIL committed briefs match the mapper: {name}")
    elif bad:
        FAILS.append(f"{name}: {bad}")
        print(f"FAIL {name}")
        for item in bad:
            print(f"  {item}")
    else:
        print(f"PASS committed briefs match the mapper: {name}")
    check_honest(name, brief)
    if name == "capped" and brief.lower().count("unknown: what comes back, a list or a page?") < 2:
        FAILS.append("capped open output is not both a slot and an Unknown")
    if name == "done" and "out of scope:" in brief:
        FAILS.append("done brief turned a hedged later line into out of scope")
    if name == "capped" and ("out of scope: a native app" in brief or "  - a native app, later" not in brief):
        FAILS.append("capped brief moved a parked later line out of the Parking lot")

for src in sorted(__import__("pathlib").Path(SHAPE).glob("*/runs/run-1/decisions.md")):
    name = src.parents[2].name
    brief = map_text(src.read_text())
    bad = failed(brief)
    if bad:
        FAILS.append(f"case {name}: {bad}")
        print(f"FAIL case {name}")
        for item in bad:
            print(f"  {item}")
    else:
        print(f"PASS case {name}")
    check_honest(name, brief)

# 1. A placeholder slot stops the mapper before any brief is written.
tbd = decisions(BASE.replace("- goal: a tiny habit tracker on my phone", "- goal: TBD"))
code, out = run_main(tbd)
tbd_bad = [] if code == 1 and "FAIL no value is a placeholder or template text" in out and "# Brief" not in out else [f"exit {code}"]
print(f"{'PASS' if not tbd_bad else 'FAIL'} a placeholder slot stops the mapper")
FAILS.extend(f"a placeholder slot stops the mapper: {item}" for item in tbd_bad)

# 2. Nested fences, including ~~~, are not decisions. A fence under Parked fails, so its text is not lost.
nested = decisions(BASE, parked="""- none
````
~~~
- Use blue paper.
~~~
````""")
nested_bad = [name for name, items in check_decisions(nested) if items]
if nested_bad != ["no code fence under Decided, Open or Parked"] or run_main(nested)[0] != 1:
    FAILS.append(f"nested fence is not a decision: {nested_bad}")
    print("FAIL nested fence is not a decision")
else:
    print("PASS nested fence is not a decision")

# 3. Lines that would trip a brief tag still pass once mapped, words unchanged.
quoted = decisions(
    """- goal: the default color is blue
- done: mark today done in under 10 seconds
- output: the current streak on the phone
- verify: mark today once and read the streak
- constraints: no accounts, it's only me
- The status is Unknown
- how: fold the paper first
- out of scope: the poster""",
    parked="- unknown until Friday",
)
quoted_brief = map_text(quoted)
quoted_bad = failed(quoted_brief)
words = ["the default color is blue", "The status is Unknown", "how: fold the paper first",
         "out of scope: the poster", "unknown until Friday"]
missing = [word for word in words if word not in quoted_brief]
if quoted_bad or missing:
    FAILS.append(f"quoted lines still pass the brief check: {quoted_bad} missing {missing}")
    print("FAIL quoted lines still pass the brief check")
else:
    print("PASS quoted lines still pass the brief check")

# 5. A Parked line always stays in the Parking lot. Only an `out of scope:` tag also puts it in Constraints.
later = decisions(
    BASE,
    parked="""- ship the poster not now
- a native app, later
- a share button for later
- voters who join later can still vote
- dark mode, maybe not now
- I think we should skip dietary tags, not now
- ship it later?
- out of scope: a watch app""",
)
later_brief = map_text(later)
later_limits = later_brief.split("- Constraints:", 1)[1].split("- Tools:", 1)[0]
later_park = later_brief.split("- Parking lot:", 1)[1].split("- Unknowns:", 1)[0]
later_bad = []
if failed(later_brief):
    later_bad.append(str(failed(later_brief)))
for line in ("ship the poster not now", "a native app, later", "a share button for later",
             "voters who join later can still vote", "dark mode, maybe not now",
             "I think we should skip dietary tags, not now", "ship it later?"):
    if line in later_limits or f"  - {line}" not in later_park:
        later_bad.append(f"moved {line}")
if "  - out of scope: a watch app" not in later_limits:
    later_bad.append("dropped the tagged out of scope line")
if "unknown: ship it later?" not in later_brief:
    later_bad.append("parked question was not kept")
print(f"{'PASS' if not later_bad else 'FAIL'} parked lines stay parked unless tagged out of scope")
FAILS.extend(f"parked lines stay parked unless tagged out of scope: {item}" for item in later_bad)

# 6. A bad file exits 1 with the checker failures, and no brief.
bad_files = {
    "bold goal": decisions(BASE.replace("- goal: a tiny habit tracker on my phone",
                                        "- **goal:** a tiny habit tracker on my phone")),
    "tilde fence": decisions(BASE.replace("- goal: a tiny habit tracker on my phone",
                                          "~~~\n- goal: a tiny habit tracker on my phone\n~~~")),
    "two-line value": decisions(BASE.replace("- goal: a tiny habit tracker on my phone",
                                             "- goal: a tiny habit tracker\n  on my phone")),
}
bad_notes = []
for label, text in bad_files.items():
    code, out = run_main(text)
    if code != 1 or "# Brief" in out or "FAIL " not in out:
        bad_notes.append(f"{label}: exit {code}")
    if label == "two-line value" and "on my phone" not in out:
        bad_notes.append("two-line value dropped the second line")
print(f"{'PASS' if not bad_notes else 'FAIL'} bad file exits 1 before mapping")
FAILS.extend(f"bad file exits 1 before mapping: {item}" for item in bad_notes)

# 7. The decide question is added unless a Decided `decide:` line answers it.
named = decisions(BASE + "\n- decide: which paper color to buy")
named_brief = map_text(named)
if "What will you decide" in named_brief or failed(named_brief):
    FAILS.append(f"decide unknown only when unnamed: {failed(named_brief)}")
    print("FAIL decide unknown only when unnamed")
else:
    print("PASS decide unknown only when unnamed")
unnamed = map_text(decisions(BASE))
if "What will you decide with the result?" not in unnamed:
    FAILS.append("decide unknown only when unnamed: missing when no line names it")
    print("FAIL decide unknown only when unnamed: missing")
for line in ("my partner and I decide together which habit counts", "the app does not decide anything for me",
             "decision: the paper color"):
    if "What will you decide with the result?" not in map_text(decisions(BASE + f"\n- {line}")):
        FAILS.append(f"decide unknown only when unnamed: {line!r} dropped it")
        print(f"FAIL decide unknown only when unnamed: {line!r}")

# 8. tools, agents, and evals fill their slots.
filled = decisions(BASE + """
- tools: a paper notebook
- agents: one person writes it
- evals: a saved link should pass, and a blank link should fail""")
filled_brief = map_text(filled)
done_block = filled_brief.split("- Done:", 1)[1].split("- Output:", 1)[0]
fill_bad = []
if failed(filled_brief):
    fill_bad.append(str(failed(filled_brief)))
for needle, slot in (("a paper notebook", "- Tools:"), ("one person writes it", "- Agents and roles:"),
                     ("a saved link should pass, and a blank link should fail", "- Evals:")):
    if needle in done_block or f"{slot} {needle}" not in filled_brief:
        fill_bad.append(needle)
if "Which tool must the run use" in filled_brief:
    fill_bad.append("tools unknown was kept beside a decided tools line")
print(f"{'PASS' if not fill_bad else 'FAIL'} tools agents evals fill their slots")
FAILS.extend(f"tools agents evals fill their slots: {item}" for item in fill_bad)

# 9. Questions follow the read-back order, and the rest stay in Unknowns.
ordered = decisions(
    BASE.replace("- done: mark today done in under 10 seconds\n", ""),
    opens="- done: what does finished look like?\n- should the streak reset at midnight?",
    stop="turn-cap",
    turns="10",
)
ordered_brief = map_text(ordered)
got_q = questions(ordered_brief)
want_q = [
    "what does finished look like?",
    "What will you decide with the result?",
    "Which tool must the run use, and what, if anything, must be written first?",
]
order_bad = []
if got_q != want_q:
    order_bad.append(f"questions {got_q}")
if "Who does the work" not in ordered_brief.split("## Questions", 1)[0]:
    order_bad.append("agents unknown was dropped")
if "Who does the work" in ordered_brief.split("## Questions", 1)[1]:
    order_bad.append("agents was asked past the third question")
if failed(ordered_brief):
    order_bad.append(str(failed(ordered_brief)))
print(f"{'PASS' if not order_bad else 'FAIL'} questions follow read-back order")
FAILS.extend(f"questions follow read-back order: {item}" for item in order_bad)

# 11. The documented loop maps from-decisions and fails when a command fails.
readme = open(os.path.join(HERE, "..", "README.md")).read()
loop = next(block for block in readme.split("```") if "set -euo pipefail" in block)
loop_bad = []
if "set -euo pipefail" not in loop or "tail" in loop or "from-decisions" not in loop:
    loop_bad.append("loop does not fail closed or skips from-decisions")
ran = subprocess.run(["bash", "-c", loop], cwd=os.path.join(HERE, ".."), capture_output=True, text=True)
if ran.returncode != 0:
    loop_bad.append(f"loop exit {ran.returncode}\n{ran.stdout}\n{ran.stderr}")
broken = loop.replace("check/check_brief.py", "check/no-such.py")
broke = subprocess.run(["bash", "-c", broken], cwd=os.path.join(HERE, ".."), capture_output=True, text=True)
if broke.returncode == 0:
    loop_bad.append("a failing command did not stop the loop")
print(f"{'PASS' if not loop_bad else 'FAIL'} readme loop maps from-decisions and fails closed")
FAILS.extend(f"readme loop maps from-decisions and fails closed: {item}" for item in loop_bad)

# 12. The docs match the checker and the handoff.
shape_readme = open(os.path.join(SKILLS, "shape-idea", "README.md")).read()
root = open(os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "..", "README.md"))).read()
shape_skill = open(os.path.join(SKILLS, "shape-idea", "SKILL.md")).read()
outcome_skill = open(os.path.join(SKILLS, "outcome", "SKILL.md")).read()
doc_bad = []
for banned in ("Open has at most 5 items", "0 through 10", "passes either way", "does not run the writing script"):
    if banned in shape_readme:
        doc_bad.append(banned)
for needed in ("from 1 through 10", "more than 5", "The check fails when a slot is in both",
               "The shape check runs the writing script"):
    if needed not in shape_readme:
        doc_bad.append(f"missing {needed}")
if "four invented ideas" not in root or "bookmark box" not in root or "three invented" in root:
    doc_bad.append("root case count")
for skill in (shape_skill, outcome_skill):
    if ORDER not in skill:
        doc_bad.append("question order")
    if "Other Decided lines" not in skill or "out of scope:" not in skill or "Unknowns" not in skill:
        doc_bad.append("handoff table")
for skill in (shape_skill, outcome_skill):
    if "ends in not now" in skill or "Constraints as `out of scope:`, and the Parking lot" not in skill:
        doc_bad.append("parked mapping row")
    if "The words stay and the tag does not" in skill:
        doc_bad.append("stated tag wording")
if 'python3 "$SKILL_DIR"/../shape-idea/check/check_decisions.py' not in outcome_skill:
    doc_bad.append("check_decisions first")
outcome_readme = open(os.path.join(HERE, "..", "README.md")).read()
for label, doc in (("shape skill", shape_skill), ("shape readme", shape_readme), ("outcome skill", outcome_skill),
                   ("outcome readme", outcome_readme)):
    for needed in ("CHECK WITH ME", "confirmed.md"):
        if needed not in doc:
            doc_bad.append(f"{label} does not name {needed}")
    # check_brief still prints ASK lines, so only shape-idea's docs drop them.
    for banned in ("ASK:",) * label.startswith("shape") + ("## Confirmed` section at the end",
                                                           "## Confirmed` at its end", "decided, or still unknown?"):
        if banned in doc:
            doc_bad.append(f"{label} still says {banned}")
print(f"{'PASS' if not doc_bad else 'FAIL'} docs match the checks")
FAILS.extend(f"docs match the checks: {item}" for item in doc_bad)

# 13. Each repro (round 2 and the round-3 review) runs the chain on the habit-tracker case: check_decisions, then the mapper,
# then check_brief. dec is check_decisions' exit; brief is check_brief's exit on the mapped brief.
HABIT = os.path.join(SHAPE, "habit-tracker", "runs", "run-1", "decisions.md")
HABIT_TEXT = open(HABIT).read()
SCRIPTS = {"dec": os.path.join(SKILLS, "shape-idea", "check", "check_decisions.py"),
           "map": os.path.join(HERE, "map_decisions.py"), "brief": os.path.join(HERE, "check_brief.py")}


def line_of(prefix):
    return next(row for row in HABIT_TEXT.splitlines() if row.startswith(prefix))


def edit(*pairs):
    text = HABIT_TEXT
    for prefix, new in pairs:
        if prefix is None:
            text = new + text
            continue
        old = line_of(prefix)
        text = text.replace(old, new.replace("&", old), 1)
    return text


def chain(text):
    """text is the decisions file, or (decisions, confirmed.md) to write a confirmed.md beside it."""
    text, confirmed = text if isinstance(text, tuple) else (text, None)
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if confirmed is not None:
        with open(os.path.join(folder, "confirmed.md"), "w", encoding="utf-8") as handle:
            handle.write(confirmed)
    dec = subprocess.run([sys.executable, SCRIPTS["dec"], path], capture_output=True, text=True)
    mapped = subprocess.run([sys.executable, SCRIPTS["map"], path], capture_output=True, text=True)
    brief_path = os.path.join(folder, "brief.md")
    open(brief_path, "w").write(mapped.stdout)
    brief = subprocess.run([sys.executable, SCRIPTS["brief"], brief_path], capture_output=True, text=True)
    return dec, mapped, brief


def block(brief, start, end):
    return brief.split(start, 1)[1].split(end, 1)[0] if start in brief else ""


ADD = "- constraints"
OUT = "- output:"
REPROS = [
    # (name, text, dec exit, brief exit or None when no brief, test on (dec stdout, brief text))
    ("unknown_out", edit((OUT, "- output: unknown")), 2, None,
     lambda d, b: 'Output: "unknown"' in d and "CHECK WITH ME" in d),
    ("notsure_out", edit((OUT, "- output: not sure yet")), 2, None,
     lambda d, b: 'Output: "not sure yet"' in d and "CHECK WITH ME" in d),
    ("tbd_phrase", edit((OUT, "- output: to be decided"), ("- verify:", "- verify: see notes")), 1, None, lambda d, b: "placeholder" in d),
    ("trap_verify", edit(("- verify:", "- verify: it looks good")), 2, None,
     lambda d, b: 'Verification: "it looks good"' in d and "CHECK WITH ME" in d),
    ("trap_done", edit(("- done:", "- done: clean")), 2, None,
     lambda d, b: 'Done: "clean"' in d and "CHECK WITH ME" in d),
    ("tools_unknown", edit((ADD, "&\n- tools: unknown: waiting to pick Python or Node")), 2, None,
     lambda d, b: 'Tools: "unknown: waiting to pick Python or Node"' in d and "CHECK WITH ME" in d),
    ("agents_unknown", edit((ADD, "&\n- agents: unknown yet")), 2, None,
     lambda d, b: 'Agents and roles: "unknown yet"' in d and "CHECK WITH ME" in d),
    ("evals_colon", edit((ADD, "&\n- evals: pass: mark today and the streak goes up; fail: miss a day and it still grows")),
     0, 0, lambda d, b: "- Evals: pass: mark today" in b and EVALS not in b),
    ("evals_labels", edit((ADD, "&\n- evals: Pass: mark today and the streak goes up; Fail: miss a day and it still grows")),
     0, 0, lambda d, b: "- Evals: Pass: mark today" in b),
    ("evals_should", edit((ADD, "&\n- evals: marking today should pass, and a missed day that keeps the streak should fail")),
     0, 0, lambda d, b: EVALS not in b),
    ("decide_vote", edit(("- the one habit", "- my partner and I decide together which habit counts")), 0, 0,
     lambda d, b: DECIDE not in block(b, "- Goal:", "- Done:") and DECIDE in block(b, "- Unknowns:", "## Questions")),
    ("decide_neg", edit(("- the one habit", "- the app does not decide anything for me")), 0, 0,
     lambda d, b: DECIDE not in block(b, "- Goal:", "- Done:") and DECIDE in block(b, "- Unknowns:", "## Questions")),
    ("notlater", edit(("- I should probably", "- send the reminder not later than 9pm")), 0, 0,
     lambda d, b: "out of scope: send" not in b and "send the reminder" in block(b, "- Parking lot:", "- Unknowns:")),
    ("ithink", edit(("- I should probably", "- I think reminders later")), 0, 0,
     lambda d, b: "out of scope: I think" not in b and "I think reminders later" in b),
    ("quoted_later", edit(("- I should probably", '- the snooze button says "Remind me later"')), 0, 0,
     lambda d, b: "out of scope: the snooze" not in b and "Remind me later" in b),
    ("not_now", HABIT_TEXT, 0, 0,
     lambda d, b: "out of scope:" not in b
     and "  - maybe later a way to share streaks" in block(b, "- Parking lot:", "- Unknowns:")),
    ("decided_oos", edit(("- the one habit", "- out of scope: syncing to a watch")), 0, 0,
     lambda d, b: "  - out of scope: syncing to a watch" in block(b, "- Constraints:", "- Tools:")
     and "watch" not in block(b, "- Done:", "- Output:")),
    ("fenced_csv", edit((OUT, "- output: a CSV with these columns:\n```\nday,done,streak\n```")), 1, None,
     lambda d, b: "code fence under Decided" in d),
    ("autolink", edit(("- verify:", "- verify: compare with <https://example.org/streak>")), 0, 0,
     lambda d, b: "<https://example.org/streak>" in b),
    ("angle_cols", edit((OUT, "- output: a CSV with `<day>` and `<streak>` columns")), 0, 0,
     lambda d, b: "`<day>`" in b),
    ("paren", edit((OUT, "- output: (CSV)")), 0, 0, lambda d, b: "- Output: (CSV)" in b),
    ("open_quote", edit(("- what should I call", '- should the button say "Done?" or "Mark"?')), 0, 0,
     lambda d, b: '"Done?"' in b),
    ("open_url", edit(("- what should I call", "- should it sync with https://example.org/sync?")), 0, 0,
     lambda d, b: "unknown: should it sync with https://example.org/sync?" in b),
    ("bom", "\ufeff" + HABIT_TEXT, 0, 0, lambda d, b: b.startswith("# Brief")),
    ("writefirst", edit((ADD, "&\n- tools: write first: none")), 2, None,
     lambda d, b: 'Tools: "write first: none"' in d and "CHECK WITH ME" in d),
    ("evals_tbdfail", edit((ADD, "&\n- evals: marking today should pass. TBD should fail.")), 1, None,
     lambda d, b: "has a case 'TBD' that is a placeholder" in d),
    ("ask_output", edit((OUT, "- output: ok")), 2, None,
     lambda d, b: 'Output: "ok"' in d and "CHECK WITH ME" in d),
    # Independent review (codex), round 3.
    ("bold_unknown", edit((OUT, "- output: **unknown**")), 2, None,
     lambda d, b: 'Output: "**unknown**"' in d and "CHECK WITH ME" in d),
    ("stated_trap", edit(("- verify:", "- verify: stated: clean")), 2, None,
     lambda d, b: 'Verification: "clean"' in d and "CHECK WITH ME" in d),
    ("decide_unknown", edit(("- the one habit", "- decide: unknown")), 2, None,
     lambda d, b: 'Goal: "unknown"' in d and "CHECK WITH ME" in d),
    ("decide_line", edit(("- the one habit", "- decide: which habit to keep")), 0, 0,
     lambda d, b: "  - which habit to keep" in block(b, "- Goal:", "- Done:") and DECIDE not in b and "decide:" not in b),
    ("evals_unknown_case", edit((ADD, "&\n- evals: pass: unknown; fail: clean")), 2, None,
     lambda d, b: 'Evals: "pass: unknown; fail: clean"' in d and "CHECK WITH ME" in d),
    ("slot_tag", edit((OUT, "- output: investigate: count the votes")), 0, 0,
     lambda d, b: "investigate: count the votes" in block(b, "- Output:", "- Constraints:")),
    ("slot_tag_home", edit(("- done:", "- done: investigate: why a streak breaks")), 0, 0,
     lambda d, b: "  - investigate: why a streak breaks" in block(b, "- Done:", "- Output:")),
    ("goal_default", edit(("- goal:", "- goal: default to a poll in the chat")), 0, 0,
     lambda d, b: "- Goal: default to a poll in the chat\n- Done:" in b),
    ("parked_hedge", edit(("- I should probably", "- later, perhaps")), 1, None, lambda d, b: "placeholder" in d),
    ("open_hole", edit(("- what should I call", "- should the bot use <channel>?")), 2, None,
     lambda d, b: 'Unknowns: "should the bot use <channel>?"' in d and "CHECK WITH ME" in d),
    ("parked_hole", edit(("- I should probably", "- ask about <channel> later")), 2, None,
     lambda d, b: 'Parking lot: "ask about <channel> later"' in d and "CHECK WITH ME" in d),
    ("open_bare_q", edit(("- what should I call", "- ?")), 1, None, lambda d, b: "placeholder" in d),
    ("how_ok", edit(("- the one habit", "- how: ok")), 2, None,
     lambda d, b: 'Done: "how: ok"' in d and "CHECK WITH ME" in d),
    ("how_line", edit(("- the one habit", "- how: fold the paper first")), 0, 0,
     lambda d, b: "  - stated: how: fold the paper first" in block(b, "- Done:", "- Output:")),
    ("done_ok", edit(("- the one habit", "- ok")), 2, None,
     lambda d, b: 'Done: "ok"' in d and "CHECK WITH ME" in d),
    ("parked_tag", edit(("- I should probably", "- investigate: the old app")), 0, 0,
     lambda d, b: "  - stated: investigate: the old app" in block(b, "- Parking lot:", "- Unknowns:")),
    ("ask_confirmed", (edit((OUT, "- output: ok")), "- Output: ok | yes\n"), 0, 0,
     lambda d, b: b.rstrip().endswith("## Confirmed\n\n- Output: ok")),
    # Round 3, fix 3. A prefix or markup hides nothing, and the brief keeps each line's meaning.
    ("stated_unknown_out", edit((OUT, "- output: stated: *unknown*")), 2, None,
     lambda d, b: 'Output: "*unknown*"' in d and "CHECK WITH ME" in d),
    ("stated_tbd_out", edit((OUT, "- output: stated: TBD")), 1, None, lambda d, b: "placeholder" in d),
    ("other_trap", edit(("- the one habit", "- it should look clean and modern")), 2, None,
     lambda d, b: 'Done: "it should look clean and modern"' in d and "CHECK WITH ME" in d),
    ("other_unknown", edit(("- the one habit", "- unknown: which browser")), 2, None,
     lambda d, b: 'Done: "unknown: which browser"' in d and "CHECK WITH ME" in d),
    ("other_question", edit(("- the one habit", "- should the streak reset at midnight?")), 2, None,
     lambda d, b: 'Done: "should the streak reset at midnight?"' in d and "CHECK WITH ME" in d),
    ("decide_maybe", edit(("- the one habit", "- decide: maybe")), 2, None,
     lambda d, b: 'Goal: "maybe"' in d and "CHECK WITH ME" in d),
    ("decide_notsure", edit(("- the one habit", "- decide: not sure yet")), 2, None,
     lambda d, b: 'Goal: "not sure yet"' in d and "CHECK WITH ME" in d),
    ("decide_ok", edit(("- the one habit", "- decide: ok")), 2, None,
     lambda d, b: 'Goal: "ok"' in d and "CHECK WITH ME" in d),
    ("decide_confirmed", (edit(("- the one habit", "- decide: maybe")), "- Goal: maybe | yes\n"), 0, 0,
     lambda d, b: "  - maybe" in block(b, "- Goal:", "- Done:") and DECIDE not in b),
    ("italic_out", edit((OUT, "- output: _unknown_")), 2, None,
     lambda d, b: 'Output: "_unknown_"' in d and "CHECK WITH ME" in d),
    ("italic_tools", edit((ADD, "&\n- tools: *unknown*: Slack or Teams")), 2, None,
     lambda d, b: 'Tools: "*unknown*: Slack or Teams"' in d and "CHECK WITH ME" in d),
    ("paren_agents", edit((ADD, "&\n- agents: (unknown yet)")), 2, None,
     lambda d, b: 'Agents and roles: "(unknown yet)"' in d and "CHECK WITH ME" in d),
    ("italic_eval", edit((ADD, "&\n- evals: pass: *unknown*; fail: a missed day keeps the streak")), 2, None,
     lambda d, b: 'Evals: "pass: *unknown*; fail: a missed day keeps the streak"' in d and "CHECK WITH ME" in d),
    ("unknown_prose_done", edit(("- done:", "- done: unknown drinks count as water")), 2, None,
     lambda d, b: 'Done: "unknown drinks count as water"' in d and "CHECK WITH ME" in d),
    ("unknown_prose_out", edit((OUT, "- output: Unknown days listed with a count")), 2, None,
     lambda d, b: 'Output: "Unknown days listed with a count"' in d and "CHECK WITH ME" in d),
    ("default_goal_decide", edit(("- goal:", "- goal: Default to water when I forget which habit"),
                                 ("- the one habit", "- decide: which habit to keep")), 0, 0,
     lambda d, b: "- Goal: Default to water" in b and DECIDE not in b),
    ("single_quote_open", edit(("- what should I call", "- Should the button say 'Done?' or 'Mark'?")), 0, 0,
     lambda d, b: "'Done?'" in b),
    ("later_mid", edit(("- I should probably", "- friends who join later can still see the streak")), 0, 0,
     lambda d, b: "out of scope: friends" not in b and "friends who join later" in block(b, "- Parking lot:", "- Unknowns:")),
    ("later_perhaps", edit(("- I should probably", "- a watch app, perhaps later")), 0, 0,
     lambda d, b: "out of scope: a watch" not in b and "a watch app, perhaps later" in b),
    ("later_comma", edit(("- I should probably", "- a watch app, later")), 0, 0,
     lambda d, b: "out of scope: a watch" not in b and "  - a watch app, later" in block(b, "- Parking lot:", "- Unknowns:")),
    ("parked_oos", edit(("- I should probably", "- out of scope: a watch app later")), 0, 0,
     lambda d, b: "out of scope: out of scope" not in b
     and "  - out of scope: a watch app later" in block(b, "- Constraints:", "- Tools:")),
    ("evals_extra_tbd", edit((ADD, "&\n- evals: pass: mark today and the streak goes up; fail: miss a day and it still"
                                   " grows; pass: TBD")), 1, None, lambda d, b: "placeholder" in d),
    ("agents_and_roles", edit((ADD, "&\n- agents and roles: me, and a friend checks it")), 0, 0,
     lambda d, b: "- Agents and roles: me, and a friend checks it" in b and AGENTS not in b),
    ("write_first", edit((ADD, "&\n- write first: a streak.json file")), 0, 0,
     lambda d, b: "  - write first: a streak.json file" in block(b, "- Tools:", "- Agents and roles:")
     and "streak.json" not in block(b, "- Done:", "- Output:")),
    ("bold_oos", edit(("- the one habit", "- **out of scope:** syncing to a watch")), 0, 0,
     lambda d, b: "  - out of scope: syncing to a watch" in block(b, "- Constraints:", "- Tools:")
     and "watch" not in block(b, "- Done:", "- Output:")),
    ("open_tools", edit(("- what should I call", "- tools: should it be a paper notebook or an app?")), 0, 0,
     lambda d, b: TOOLS not in b
     and "  - unknown: should it be a paper notebook or an app?" in block(b, "- Tools:", "- Agents and roles:")),
    ("fence_open", edit(("- what should I call", "&\n```\n- sync between phones?\n```")), 1, None,
     lambda d, b: "under Open" in d),
    ("fence_parked", edit(("- I should probably", "&\n~~~\n- sync between phones, not now\n~~~")), 1, None,
     lambda d, b: "under Parked" in d),
    # Round 4. Unknown is never ready, a Parked line stays parked unless tagged, and the mapper agrees with check_brief.
    ("r4_tools_for_now", edit((ADD, "&\n- tools: Unknown for now")), 2, None,
     lambda d, b: 'Tools: "Unknown for now"' in d and "CHECK WITH ME" in d),
    ("r4_tools_comma", edit((ADD, "&\n- tools: unknown, Slack or Teams")), 2, None,
     lambda d, b: 'Tools: "unknown, Slack or Teams"' in d and "CHECK WITH ME" in d),
    ("r4_output_for_now", edit((OUT, "- output: unknown for now")), 2, None,
     lambda d, b: 'Output: "unknown for now"' in d and "CHECK WITH ME" in d),
    ("r4_agents_for_now", edit((ADD, "&\n- agents: unknown for now")), 2, None,
     lambda d, b: 'Agents and roles: "unknown for now"' in d and "CHECK WITH ME" in d),
    ("r4_decide_so_far", edit(("- the one habit", "- decide: unknown so far")), 2, None,
     lambda d, b: 'Goal: "unknown so far"' in d and "CHECK WITH ME" in d),
    ("r4_output_quoted", edit((OUT, '- output: "unknown": CSV or JSON')), 2, None,
     lambda d, b: 'Output: "\"unknown\": CSV or JSON"' in d and "CHECK WITH ME" in d),
    ("r4_output_stated_dash", edit((OUT, "- output: stated: Unknown - CSV or JSON")), 2, None,
     lambda d, b: 'Output: "Unknown - CSV or JSON"' in d and "CHECK WITH ME" in d),
    ("r4_evals_unknown_tails", edit((ADD, "&\n- evals: pass: unknown for now; fail: unknown, ask Sam")), 2, None,
     lambda d, b: 'Evals: "pass: unknown for now; fail: unknown, ask Sam"' in d and "CHECK WITH ME" in d),
    ("in_file_confirmed", edit((OUT, "- output: ok")) + "\n## Confirmed\n\n- Output: ok\n", 1, None,
     lambda d, b: "FAIL" in d),
    ("r4_unknown_prose_confirmed", (edit((OUT, "- output: Unknown days listed with a count")),
                                    "- Output: Unknown days listed with a count | yes\n"), 0, 0,
     lambda d, b: "- Output: Unknown days listed with a count" in b),
    ("r4_parked_oos_ai", edit(("- I should probably", "- out of scope: AI")), 2, None,
     lambda d, b: 'Constraints: "out of scope: AI"' in d and "CHECK WITH ME" in d),
    ("r4_parked_bold_oos_ai", edit(("- I should probably", "- **out of scope:** AI")), 2, None,
     lambda d, b: 'Constraints: "out of scope: AI"' in d and "CHECK WITH ME" in d),
    ("r4_parked_oos_confirmed", (edit(("- I should probably", "- out of scope: AI")),
                                 "- Constraints: out of scope: AI | yes\n"), 0, 0,
     lambda d, b: "  - out of scope: AI" in block(b, "- Constraints:", "- Tools:")),
    ("r4_dark_mode", edit(("- I should probably", "- dark mode, maybe not now")), 0, 0,
     lambda d, b: "out of scope: dark" not in b and "  - dark mode, maybe not now" in block(b, "- Parking lot:", "- Unknowns:")),
    ("r4_skip_tags", edit(("- I should probably", "- I think we should skip dietary tags, not now")), 0, 0,
     lambda d, b: "out of scope: I think" not in b
     and "  - I think we should skip dietary tags, not now" in block(b, "- Parking lot:", "- Unknowns:")),
    ("r4_apostrophe_question", edit(("- what should I call", "- Should the button say 'What's next?' or 'Continue'?")), 0, 0,
     lambda d, b: "unknown: Should the button say 'What's next?' or 'Continue'?" in b),
    ("r4_closing_quote_question", edit(("- what should I call", '- should the label say "Continue?"')), 0, 0,
     lambda d, b: '1. ' in b and 'should the label say "Continue?"\n' in b),
    ("r4_open_tools_bare", edit(("- what should I call", "- tools: ?")), 1, None, lambda d, b: "placeholder" in d),
    ("r4_open_evals_tbd", edit(("- what should I call", "- evals: TBD?")), 1, None, lambda d, b: "placeholder" in d),
    ("r4_open_agents_unknown", edit(("- what should I call", "- agents: unknown: ?")), 1, None, lambda d, b: "placeholder" in d),
    ("r4_open_tools_hole", edit(("- what should I call", "- tools: Should the poll run in <channel>?")), 2, None,
     lambda d, b: 'Tools: "Should the poll run in <channel>?"' in d and "CHECK WITH ME" in d),
    ("r4_decided_hole", edit(("- the one habit", "- the form submits on <Enter>")), 2, None,
     lambda d, b: 'Done: "the form submits on <Enter>"' in d and "CHECK WITH ME" in d),
    ("r4_parked_hole", edit(("- I should probably", "- the form submits on <Enter>")), 2, None,
     lambda d, b: 'Parking lot: "the form submits on <Enter>"' in d and "CHECK WITH ME" in d),
    ("r4_evals_unlabeled", edit((ADD, "&\n- evals: a poll with 3 choices works and a poll with none errors")), 2, None,
     lambda d, b: 'Evals: "a poll with 3 choices works and a poll with none errors"' in d and "CHECK WITH ME" in d),
    ("r4_bold_tools", edit((ADD, "&\n- **tools:** Slack only")), 0, 0,
     lambda d, b: "- Tools: Slack only" in b and TOOLS not in b and "Slack" not in block(b, "- Done:", "- Output:")),
    ("r4_bold_decide", edit(("- the one habit", "- **decide:** whether to keep the bot")), 0, 0,
     lambda d, b: "  - whether to keep the bot" in block(b, "- Goal:", "- Done:") and DECIDE not in b),
    ("r4_singular_tool", edit((ADD, "&\n- tool: Slack only")), 0, 0, lambda d, b: "- Tools: Slack only" in b),
    ("r4_singular_eval", edit((ADD, "&\n- eval: pass: mark today and the streak goes up; fail: miss a day and it still grows")),
     0, 0, lambda d, b: "- Evals: pass: mark today" in b and EVALS not in b),
    # Round 5. One normalization for an answer's first word, no crash on an empty label, code spans kept, and the
    # stock decide question never shares Goal with the user's value.
    ("r5_paren_unknown", edit((OUT, "- output: (unknown), CSV or JSON")), 2, None,
     lambda d, b: 'Output: "(unknown), CSV or JSON"' in d and "CHECK WITH ME" in d),
    ("r5_link_unknown", edit((OUT, "- output: [unknown](https://example.org/status)")), 2, None,
     lambda d, b: 'Output: "[unknown](https://example.org/status)"' in d and "CHECK WITH ME" in d),
    ("r5_empty_decide", edit(("- the one habit", "- decide: stated:")), 1, None, lambda d, b: "decide: needs a value" in d),
    ("r5_empty_tools", edit((ADD, "&\n- tools: stated:")), 1, None, lambda d, b: "tools: needs a value" in d),
    ("r5_empty_other", edit(("- the one habit", "- stated:")), 1, None, lambda d, b: "no value" in d),
    ("r5_code_span", edit(("- the one habit", "- stated: `<col>` is the literal header")), 0, 0,
     lambda d, b: "  - `<col>` is the literal header\n" in block(b, "- Done:", "- Output:")),
    ("r5_parked_code", edit(("- I should probably", "- stated: run `make check` first")), 0, 0,
     lambda d, b: "  - run `make check` first\n" in block(b, "- Parking lot:", "- Unknowns:")),
    ("r5_dark_goal", edit(("- goal:", "- goal: default new users to dark mode")), 0, 0,
     lambda d, b: "- Goal: default new users to dark mode\n- Done:" in b
     and DECIDE in block(b, "- Unknowns:", "## Questions")),
    ("r5_fullwidth_oos", edit(("- I should probably", "- out of scope\uff1acatering")), 0, 0,
     lambda d, b: "  - out of scope: catering" in block(b, "- Constraints:", "- Tools:")),
    ("r5_open_hole", edit(("- what should I call", "- Should it press <Enter> to confirm each move?")), 2, None,
     lambda d, b: 'Unknowns: "Should it press <Enter> to confirm each move?"' in d and "CHECK WITH ME" in d),
    ("r5_unknown_senders", edit((ADD, "- constraints: unknown senders get nothing")), 2, None,
     lambda d, b: 'Constraints: "unknown senders get nothing"' in d and "CHECK WITH ME" in d),
    ("r5_compound_oos", edit((ADD, "&\n- out of scope: stated: unknown for now")), 2, None,
     lambda d, b: 'Constraints: "out of scope: unknown for now"' in d and "CHECK WITH ME" in d),
    ("r5_compound_how", edit((ADD, "&\n- stated: how: clean")), 2, None,
     lambda d, b: 'Done: "how: clean"' in d and "CHECK WITH ME" in d),
]
repro_bad = []
for name, text, want_dec, want_brief, ok in REPROS:
    TEXTS.append(text[0] if isinstance(text, tuple) else text)
    dec, mapped, brief = chain(text)
    got_brief = brief.returncode if mapped.returncode == 0 else None
    if mapped.returncode == 0 and "# Brief" not in mapped.stdout:
        got_brief = "empty"
    if mapped.returncode != 0 and (mapped.returncode != dec.returncode or "# Brief" in mapped.stdout):
        repro_bad.append(f"{name}: mapper exit {mapped.returncode} printed a brief or disagreed with dec")
    if (dec.returncode, got_brief) != (want_dec, want_brief) or not ok(dec.stdout, mapped.stdout):
        repro_bad.append(f"{name}: dec={dec.returncode} brief={got_brief}, wanted {want_dec}/{want_brief}"
                         f"\n{dec.stdout[-400:]}\n{brief.stdout[-400:]}")
print(f"{'PASS' if not repro_bad else 'FAIL'} repros, {len(REPROS) - len(repro_bad)}/{len(REPROS)}")
FAILS.extend(f"round-2 repro {item}" for item in repro_bad)

# 14. A path that cannot be read is a usage error: exit 3, one line, no traceback.
BINARY = os.path.join(tempfile.mkdtemp(), "binary.md")
open(BINARY, "wb").write(b"# Decisions\n\xff\xfe\n")
for label, path in (("missing path", os.path.join(tempfile.mkdtemp(), "missing.md")),
                    ("directory", tempfile.mkdtemp()), ("non-UTF-8 file", BINARY)):
    got = subprocess.run([sys.executable, SCRIPTS["map"], path], capture_output=True, text=True)
    said = (got.stdout + got.stderr).strip().splitlines()
    ok = got.returncode == 3 and len(said) == 1 and "Traceback" not in got.stderr
    print(f"{'PASS' if ok else 'FAIL'} {label} exits 3")
    if not ok:
        FAILS.append(f"{label} exits 3: exit {got.returncode}, said {said}")

# 15. Invariant on every decisions text in these tests, the cases and the fixtures: the mapper exits as
# check_decisions does, and a brief it prints passes check_brief.
FIXTURES = os.path.join(SKILLS, "shape-idea", "check", "fixtures")
files = [os.path.join(FIXTURES, f) for f in sorted(os.listdir(FIXTURES)) if f.endswith(".md")]
files += [os.path.join(CASES, name, "decisions.md") for name in ("done", "capped")]
files += [str(p) for p in sorted(__import__("pathlib").Path(SHAPE).glob("*/runs/run-1/decisions.md"))]
TEXTS += [open(f, encoding="utf-8").read() for f in files]
invariant_bad = []
for number, text in enumerate(TEXTS):
    path = os.path.join(tempfile.mkdtemp(), "decisions.md")
    open(path, "w", encoding="utf-8").write(text)
    with contextlib.redirect_stdout(io.StringIO()):
        dec = check_decisions_main(path)
    code, brief = run_main(text)
    bad = [] if code == dec else [f"mapper exit {code}, check_decisions exit {dec}"]
    if code == 0:
        bad += [f for _, fails in check(brief) for f in fails] + ask_lines(brief)
    if bad:
        invariant_bad.append(f"{number}: {bad}\n{text[:300]}")
print(f"{'PASS' if not invariant_bad else 'FAIL'} invariant, {len(TEXTS) - len(invariant_bad)}/{len(TEXTS)}")
FAILS.extend(f"invariant {item}" for item in invariant_bad)

if __name__ == "__main__":
    print(f"{'PASS' if not FAILS else 'FAIL'} map briefs")
    for item in FAILS:
        print(item)
    sys.exit(1 if FAILS else 0)
