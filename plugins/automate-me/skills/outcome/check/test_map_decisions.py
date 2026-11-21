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
from map_decisions import main, map_text  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import check as check_decisions  # noqa: E402

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


def decisions(decided, opens="- none", parked="- none", stop="done", turns="1"):
    return f"""# Decisions: sample

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
"""


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
    if brief.rstrip("\n") != want.rstrip("\n"):
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
    if name == "capped" and "out of scope: a native app later" not in brief:
        FAILS.append("capped brief dropped the standalone later line")

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

# 1. A placeholder stays the only item in Goal, Constraints, and Verification.
tbd = decisions(BASE.replace("- goal: a tiny habit tracker on my phone", "- goal: TBD")
                .replace("- verify: mark today once and read the streak", "- verify: TBD")
                .replace("- constraints: no accounts, it's only me", "- constraints: TBD"))
tbd_brief = map_text(tbd)
tbd_detail = " ".join(item for _, items in check(tbd_brief) for item in items)
goal = tbd_brief.split("- Done:", 1)[0]
limits = tbd_brief.split("- Constraints:", 1)[1].split("- Tools:", 1)[0]
verify = tbd_brief.split("- Verification:", 1)[1].split("- Unknowns:", 1)[0]
hidden = []
for slot in ("Goal", "Constraints", "Verification"):
    if f"slot {slot} is only a placeholder" not in tbd_detail:
        hidden.append(f"brief did not flag {slot}: {tbd_detail}")
if "What will you decide" in goal or "Report only" in limits or "Every claim names" in verify:
    hidden.append("mapper text hid a placeholder")
code, out = run_main(tbd)
if code != 1 or "slot values are not placeholders" not in out or "# Brief" in out:
    hidden.append(f"main did not stop: exit {code}")
print(f"{'PASS' if not hidden else 'FAIL'} mapped placeholders stay visible")
FAILS.extend(f"mapped placeholders stay visible: {item}" for item in hidden)

# 2. Nested fences, including ~~~, are not decisions.
nested = decisions(BASE + """
````
~~~
- Use blue paper.
~~~
````""")
nested_bad = [name for name, items in check_decisions(nested) if items]
if nested_bad or "blue paper" in map_text(nested).lower():
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
- out of scope: the poster
- clean""",
    parked="- unknown until Friday",
)
quoted_brief = map_text(quoted)
quoted_bad = failed(quoted_brief)
words = ["the default color is blue", "The status is Unknown", "how: fold the paper first",
         "out of scope: the poster", "clean", "unknown until Friday"]
missing = [word for word in words if word not in quoted_brief]
if quoted_bad or missing:
    FAILS.append(f"quoted lines still pass the brief check: {quoted_bad} missing {missing}")
    print("FAIL quoted lines still pass the brief check")
else:
    print("PASS quoted lines still pass the brief check")

# 5. Later means not now, or later on its own.
later = decisions(
    BASE,
    parked="""- ship the poster not now
- a native app later
- no later than Friday
- ship it later?
- maybe later
- dietary tags later, not sure""",
)
later_brief = map_text(later)
later_limits = later_brief.split("- Constraints:", 1)[1].split("- Tools:", 1)[0]
later_park = later_brief.split("- Parking lot:", 1)[1].split("- Unknowns:", 1)[0]
later_bad = []
if failed(later_brief):
    later_bad.append(str(failed(later_brief)))
for line in ("ship the poster not now", "a native app later"):
    if f"out of scope: {line}" not in later_limits or line not in later_park:
        later_bad.append(f"dropped {line}")
for line in ("no later than Friday", "ship it later?", "maybe later", "dietary tags later, not sure"):
    if f"out of scope: {line}" in later_brief:
        later_bad.append(f"scoped {line}")
if "unknown: ship it later?" not in later_brief or "ship it later?" not in later_park:
    later_bad.append("parked question was not kept")
print(f"{'PASS' if not later_bad else 'FAIL'} later means not now or standalone later")
FAILS.extend(f"later means not now or standalone later: {item}" for item in later_bad)

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

# 7. The decide question is added only when no Decided line names it.
named = decisions(BASE + "\n- decision: the paper color")
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
if 'python3 "$SKILL_DIR"/../shape-idea/check/check_decisions.py' not in outcome_skill:
    doc_bad.append("check_decisions first")
print(f"{'PASS' if not doc_bad else 'FAIL'} docs match the checks")
FAILS.extend(f"docs match the checks: {item}" for item in doc_bad)

if __name__ == "__main__":
    print(f"{'PASS' if not FAILS else 'FAIL'} map briefs")
    for item in FAILS:
        print(item)
    sys.exit(1 if FAILS else 0)
