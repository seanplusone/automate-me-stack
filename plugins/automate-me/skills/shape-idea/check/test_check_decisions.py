"""Run: python3 check/test_check_decisions.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import check, main  # noqa: E402

FAILS = []
RAN = []

GOOD = """# Decisions: water habit

## Decided

- goal: a tiny habit tracker on my phone
- done: mark today done in under 10 seconds
- output: the current streak on the phone
- verify: mark today once and read the streak
- constraints: no accounts, it's only me
- the one habit is drinking water

## Open

- Do you want a reminder?

## Parked

- share streaks with friends

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints and done go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
"""

HANDOFF = """## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints and done go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
"""

PRESENT = "sections present once"
ORDER = "sections in order"
QUESTION = "every open item ends with a question"
STOP = "stop reason is done, turn-cap, or open-cap"
TURNS = "turn count recorded and at most 10"
SLOTS = "every slot is decided or open"
DONE = "stop matches the file"
MATCH = "stop matches the file"
ONE_LINE = "no item longer than one line"
NEXT = "handoff names outcome"
WRITING = "handoff says writing pass"


def failed(text):
    return {name for name, fails in check(text) if fails}


def expect(name, text, want):
    RAN.append(name)
    got = failed(text)
    if got != want:
        FAILS.append(f"{name}: wanted {sorted(want)}, got {sorted(got)}")


def swap(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new)


def opens(n):
    lines = "\n".join(f"- Open question {i}?" for i in range(1, n + 1))
    return swap("- Do you want a reminder?", lines)


def missing_slot(line):
    text = swap(line, "")
    text = swap("- stop: done", "- stop: turn-cap", text)
    return swap("- turns: 1", "- turns: 10", text)


expect("good file passes", GOOD, set())
expect("missing Handoff", swap(HANDOFF, ""), {PRESENT})
expect("open without question", swap("- Do you want a reminder?", "- reminders are not settled"), {QUESTION})
expect("question mark not at the end", swap("- Do you want a reminder?", "- Do you want a reminder? Maybe."), {QUESTION})
expect("six non-slot opens do not block done", opens(6), set())
expect("5 open items pass", opens(5), set())
expect("turn 11", swap("- turns: 1", "- turns: 11"), {TURNS})
expect("turns 0", swap("- turns: 1", "- turns: 0"), {TURNS})
expect("unicode digit turn does not crash", swap("- turns: 1", "- turns: ²"), {TURNS})
expect("turns 10 passes", swap("- turns: 1", "- turns: 10"), set())
expect("open-cap on turn 1 fails", swap("- stop: done", "- stop: open-cap"), {MATCH})
expect("missing goal", missing_slot("- goal: a tiny habit tracker on my phone\n"), {SLOTS})
expect("missing done", missing_slot("- done: mark today done in under 10 seconds\n"), {SLOTS})
expect("missing output", missing_slot("- output: the current streak on the phone\n"), {SLOTS})
expect("missing verify", missing_slot("- verify: mark today once and read the streak\n"), {SLOTS})
expect("missing constraints", missing_slot("- constraints: no accounts, it's only me\n"), {SLOTS})
expect("stop done without done", swap("- done: mark today done in under 10 seconds\n", ""), {SLOTS, DONE})
expect("stop done with output still open",
       swap("- output: the current streak on the phone\n", "",
            swap("- Do you want a reminder?", "- output: what comes back, a list or a page?\n- Do you want a reminder?")),
       {DONE})
expect("turn-cap with done in Open passes",
       swap("- turns: 1", "- turns: 10",
            swap("- Do you want a reminder?", "- done: what does finished look like?\n- Do you want a reminder?",
                 swap("- stop: done", "- stop: turn-cap", swap("- done: mark today done in under 10 seconds\n", "")))),
       set())
expect("duplicate goal", GOOD.replace("- goal: a tiny habit tracker on my phone\n",
                                      "- goal: a tiny habit tracker on my phone\n- goal: another one\n"),
       {"no duplicate slot"})
expect("empty goal value", swap("- goal: a tiny habit tracker on my phone", "- goal:"),
       {"slot values are not empty"})
expect("writing pass does not excuse slop",
       swap("- goal: a tiny habit tracker on my phone", "- goal: we will leverage a robust plan. It delves."),
       {"prose passes the writing check"})
expect("bad stop reason", swap("- stop: done", "- stop: later"), {STOP})
expect("missing turns", swap("- turns: 1\n", ""), {TURNS})
expect("turns is not a number", swap("- turns: 1", "- turns: ten"), {TURNS})
expect("missing next", swap("- next: /automate-me:outcome\n", ""), {NEXT})
expect("missing writing pass", swap("- writing: pass\n", ""), {WRITING})
expect("item longer than one line",
       swap("- goal: a tiny habit tracker on my phone", "- goal: a tiny habit tracker\n  on my phone"), {ONE_LINE})
expect("repeated section", GOOD + "\n## Decided\n\n- again\n", {PRESENT})
rest = swap(HANDOFF, "").replace("# Decisions: water habit\n\n", "", 1)
expect("sections out of order", "# Decisions: water habit\n\n" + HANDOFF + "\n" + rest, {ORDER})
expect("lone none in Open is empty", swap("- Do you want a reminder?", "- none"), set())
expect("a non-slot line is optional", swap("- the one habit is drinking water\n", ""), set())


def write(text):
    path = os.path.join(tempfile.mkdtemp(), "decisions.md")
    open(path, "w").write(text)
    return path


def expect_exit(name, text, code):
    RAN.append(name)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        got = main(write(text))
    if got != code:
        FAILS.append(f"{name}: exit {got}, wanted {code}\n{buf.getvalue()}")


expect_exit("exit 0 on a good file", GOOD, 0)
expect_exit("exit 1 on a bad file", swap(HANDOFF, ""), 1)

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_decisions.py")


def expect_code(name, args, code):
    RAN.append(name)
    got = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True)
    if got.returncode != code:
        FAILS.append(f"{name}: exit {got.returncode}, wanted {code}")


expect_code("usage exits 2", [], 2)
expect_code("help exits 0", ["--help"], 0)

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
