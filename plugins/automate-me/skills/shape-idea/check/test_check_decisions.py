"""Run: python3 check/test_check_decisions.py"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import asks, check, main  # noqa: E402

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
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
"""

HANDOFF = """## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
- writing: pass
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
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


TEXTS = []


def expect(name, text, want):
    TEXTS.append(text)
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
expect("six non-slot opens do not block done after turn 1",
       swap("- turns: 1", "- turns: 3", opens(6)), set())
expect("5 open items pass", opens(5), set())
expect("turn 11", swap("- turns: 1", "- turns: 11"), {TURNS})
expect("turns 0", swap("- turns: 1", "- turns: 0"), {TURNS})
expect("unicode digit turn does not crash", swap("- turns: 1", "- turns: ²"), {TURNS})
expect("turns 10 passes", swap("- turns: 1", "- turns: 10"), set())
expect("open-cap on turn 1 fails", swap("- stop: done", "- stop: open-cap"),
       {MATCH, "stop is the first match"})
expect("writing and stop ignore case",
       swap("- stop: done", "- stop: DONE", swap("- writing: pass", "- writing: PASS",
            swap("- turns: 1", "- turns: 03"))), set())
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
PLACE = "slot values are not placeholders"
for token in ("TBD", "TODO", "n/a", "...", "<the want...>"):
    expect(f"placeholder slot values fail {token}",
           swap("- goal: a tiny habit tracker on my phone", f"- goal: {token}"), {PLACE})
expect("placeholder slot values fail ?",
       swap("- goal: a tiny habit tracker on my phone", "- goal: ?"),
       {PLACE, "slot values are not empty"})
expect("decided value ending in a question fails",
       swap("- goal: a tiny habit tracker on my phone", "- goal: a tiny habit tracker?"), {PLACE})
open_tbd = swap("- output: the current streak on the phone\n", "")
open_tbd = swap("- Do you want a reminder?", "- output: TBD?", open_tbd)
open_tbd = swap("- stop: done", "- stop: turn-cap", open_tbd)
open_tbd = swap("- turns: 1", "- turns: 10", open_tbd)
expect("open placeholder slot fails", open_tbd, {PLACE})
expect("question mark in a url or code",
       swap("- Do you want a reminder?",
            "- see https://example.com/a?b=1 and the `flag?` bit?"), set())
expect("empty tools line is rejected",
       swap("- the one habit is drinking water", "- the one habit is drinking water\n- tools:"),
       {"tools, agents, evals, and decide lines are usable"})
expect("tools agents evals lines pass when usable",
       swap("- the one habit is drinking water",
            "- the one habit is drinking water\n- tools: a paper notebook\n- agents: one person writes it\n- evals: a saved link should pass, and a blank link should fail"),
       set())
NESTED = """- the one habit is drinking water
````
~~~
- Use blue paper.
~~~
````"""
FENCE = "no code fence under Decided, Open or Parked"
expect("a fence under Decided fails, so its text is not lost",
       swap("- the one habit is drinking water", NESTED), {FENCE})
expect("a fence under an output slot fails",
       swap("- output: the current streak on the phone",
            "- output: a CSV with these columns:\n```\nday,done,streak\n```"), {FENCE})
expect("a nested fence under Parked fails too",
       swap("- share streaks with friends", "- share streaks with friends\n" + NESTED.split("\n", 1)[1]), {FENCE})

EXTRA = "tools, agents, evals, and decide lines are usable"
HABIT = "- the one habit is drinking water"


def added(line):
    return swap(HABIT, f"{HABIT}\n{line}")


for label in ("pass: mark today and the streak goes up; fail: miss a day and it still grows",
              "Pass: mark today and the streak goes up; Fail: miss a day and it still grows",
              "marking today should pass, and a missed day that keeps the streak should fail"):
    expect(f"evals line passes: {label[:20]}", added(f"- evals: {label}"), set())
expect("evals with a TBD fail case fails", added("- evals: marking today should pass. TBD should fail."), {EXTRA})
expect("evals with only a pass case fails", added("- evals: pass: mark today"), {EXTRA})
expect("tools write first none fails", added("- tools: write first: none"), {EXTRA})


def reason(text, check_name):
    return " ".join(fail for name, fails in check(text) if name == check_name for fail in fails)


for label, text, check_name in (
        ("output: unknown", swap("- output: the current streak on the phone", "- output: unknown"), PLACE),
        ("tools: unknown: X or Y", added("- tools: unknown: waiting to pick Python or Node"), EXTRA),
        ("agents: unknown yet", added("- agents: unknown yet"), EXTRA)):
    expect(f"unknown is not ready: {label}", text, {check_name})
    RAN.append(f"unknown message: {label}")
    if "move it to Open as a question" not in reason(text, check_name):
        FAILS.append(f"unknown message: {label}: {reason(text, check_name)}")
for label, line in (("verify: it looks good", "- verify: it looks good"), ("done: clean", "- done: clean")):
    slot = line[2:line.index(":")]
    old = next(row for row in GOOD.splitlines() if row.startswith(f"- {slot}:"))
    expect(f"trap word slot fails: {label}", swap(old, line), {PLACE})
for value in ("to be decided", "same as above", "fill in later"):
    expect(f"placeholder phrase fails: {value}",
           swap("- output: the current streak on the phone", f"- output: {value}"), {PLACE})
expect("a phrase off the fixed list passes to the read-back",
       swap("- output: the current streak on the phone", "- output: not sure yet"), set())
expect("an autolink is not template text",
       swap("- verify: mark today once and read the streak",
            "- verify: compare with <https://example.org/streak>"), set())
expect("angle brackets in code are not template text",
       swap("- output: the current streak on the phone", "- output: a CSV with `<day>` and `<streak>` columns"), set())
expect("an Open question may end in a URL",
       swap("- Do you want a reminder?", "- should it sync with https://example.org/sync?"), set())
expect("an Open question may quote a question",
       swap("- Do you want a reminder?", '- should the button say "Done?" or "Mark"?'), set())
expect("two questions in one Open item still fail",
       swap("- Do you want a reminder?", "- Do you want a reminder? Or a badge?"), {QUESTION})
for label, line in (("bold", "- **goal:** a tiny habit tracker on my phone"),
                    ("numbered", "1. goal: a tiny habit tracker on my phone")):
    text = missing_slot("- goal: a tiny habit tracker on my phone\n").replace("## Open", f"{line}\n\n## Open")
    RAN.append(f"{label} slot names the fix")
    if "no bold or number" not in reason(text, SLOTS):
        FAILS.append(f"{label} slot names the fix: {reason(text, SLOTS)}")

# A value check_brief would ask about is a yes/no question for the person, not a ready line.
OK_OUT = swap("- output: the current streak on the phone", "- output: ok")
RAN.append("ask lists the value")
if asks(OK_OUT) != [("Output", "ok")] or failed(OK_OUT):
    FAILS.append(f"ask lists the value: {asks(OK_OUT)} {failed(OK_OUT)}")
RAN.append("ask on an evals case body")
if asks(added("- evals: pass: ok; fail: a missed day keeps the streak")) != [("Evals", "ok")]:
    FAILS.append("ask on an evals case body")
RAN.append("ask on another Decided line, which lands in Done")
if asks(swap(HABIT, "- maybe")) != [("Done", "maybe")]:
    FAILS.append(f"ask on another Decided line: {asks(swap(HABIT, '- maybe'))}")
CONFIRMED = OK_OUT + "\n## Confirmed\n\n- Output: ok\n"
expect("a Confirmed section after Handoff passes", CONFIRMED, set())
RAN.append("a confirmation lifts the ask")
if asks(CONFIRMED):
    FAILS.append(f"a confirmation lifts the ask: {asks(CONFIRMED)}")
expect("a confirmation never lifts a fail",
       swap("- output: ok", "- output: TBD", CONFIRMED).replace("- Output: ok", "- Output: TBD"), {PLACE})
expect("a Confirmed line needs a brief slot", CONFIRMED.replace("- Output: ok", "- output ok"),
       {"confirmed lines name a brief slot"})
expect("Confirmed before Handoff is out of order",
       OK_OUT.replace("## Handoff", "## Confirmed\n\n- Output: ok\n\n## Handoff"), {ORDER})


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
expect_exit("exit 2 on a value to confirm", OK_OUT, 2)
expect_exit("exit 0 once confirmed", CONFIRMED, 0)
expect_exit("exit 1 beats an ask", swap(HANDOFF, "", OK_OUT), 1)
expect_exit("a UTF-8 BOM is not text", "\ufeff" + GOOD, 0)
RAN.append("ask line format")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    main(write(OK_OUT))
if "ASK: Output: Is 'ok' a real answer for Output?" not in buf.getvalue() or "ASK decisions:" not in buf.getvalue():
    FAILS.append(f"ask line format: {buf.getvalue()}")

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_decisions.py")


def expect_code(name, args, code):
    RAN.append(name)
    got = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True)
    if got.returncode != code:
        FAILS.append(f"{name}: exit {got.returncode}, wanted {code}")


expect_code("usage exits 3", [], 3)
expect_code("help exits 0", ["--help"], 0)

# Round 3, fix 3. Every Decided line is judged by the same rules, whatever its label or prefix.
READY = "other Decided and Parked lines are ready"
OUT_LINE = "- output: the current streak on the phone"


def out(value):
    return swap(OUT_LINE, f"- output: {value}")


def open_q(line):
    return swap("- Do you want a reminder?", line)


def parked(line):
    return swap("- share streaks with friends", line)


for label, text, check_name, words in (
        ("stated italic unknown output", out("stated: *unknown*"), PLACE, "move it to Open as a question"),
        ("stated TBD output", out("stated: TBD"), PLACE, "placeholder"),
        ("italic unknown output", out("_unknown_"), PLACE, "move it to Open as a question"),
        ("quoted unknown output", out('"unknown"'), PLACE, "move it to Open as a question"),
        ("paren unknown yet agents", added("- agents: (unknown yet)"), EXTRA, "move it to Open as a question"),
        ("italic unknown tools", added("- tools: *unknown*: Slack or Teams"), EXTRA, "move it to Open as a question"),
        ("italic unknown eval case", added("- evals: pass: *unknown*; fail: a missed day keeps the streak"), EXTRA,
         "move it to Open as a question"),
        ("extra TBD eval case", added("- evals: pass: mark today and the streak goes up; fail: miss a day and it"
                                      " still grows; pass: TBD"), EXTRA, "placeholder"),
        ("other line trap", added("- it should look clean and modern"), READY, "no visible signal"),
        ("other line unknown", added("- unknown: which browser"), READY, "move it to Open as a question"),
        ("other line stated unknown", added("- stated: unknown"), READY, "move it to Open as a question"),
        ("other line stated TBD", added("- stated: TBD"), "no placeholder line", "placeholder"),
        ("other line question", added("- should a link expire?"), READY, "move it to Open"),
        ("parked unknown", parked("- unknown"), READY, "move it to Open as a question"),
        ("parked trap", parked("- clean"), READY, "no visible signal"),
        ("fence under Open", open_q("- Do you want a reminder?\n```\n- sync between phones?\n```"), FENCE, "under Open"),
        ("fence under Parked", parked("- share streaks with friends\n~~~\n- sync between phones, not now\n~~~"), FENCE,
         "under Parked")):
    expect(f"fix3 fails: {label}", text, {check_name})
    RAN.append(f"fix3 message: {label}")
    if words not in reason(text, check_name):
        FAILS.append(f"fix3 message: {label}: {reason(text, check_name)}")

expect("fix3 fails: an Open unknown with no question", open_q("- unknown: ?"), {QUESTION})
expect("fix3 fails: an Open slot unknown with no question", swap(OUT_LINE, "", open_q("- output: unknown: ?")).replace(
    "- stop: done", "- stop: turn-cap").replace("- turns: 1", "- turns: 10"), {PLACE})

GOAL_LINE = "- goal: a tiny habit tracker on my phone"
for label, text in (
        ("unknown prose in done", swap("- done: mark today done in under 10 seconds",
                                       "- done: unknown file types go to an Other folder")),
        ("Unknown prose in output", out("Unknown senders listed with a count")),
        ("unknown-file prose in tools", added("- tools: Unknown-file detector script in tools/")),
        ("default goal with a decide line", added("- decide: which habit to keep").replace(
            GOAL_LINE, "- goal: Default to water when I forget which habit")),
        ("single quoted label in an Open question", open_q("- Should the button say 'Vote?' or 'Pick'?")),
        ("parens in an Open question", open_q("- should it be a list (or a page?) or both?")),
        ("unknown prose in Parked", parked("- unknown senders get their own folder")),
        ("agents and roles label", added("- agents and roles: me, and a friend checks it")),
        ("write first label", added("- write first: a streak.json file")),
        ("bold out of scope label", added("- **out of scope:** syncing to a watch"))):
    expect(f"fix3 passes: {label}", text, set())

expect("fix3 a curly quoted label is not a second question, though the writing check bans curly quotes",
       open_q("- Should the button say \u2018Vote?\u2019 or \u2018Pick\u2019?"), {"prose passes the writing check"})
expect("fix3 fails: default goal without a decide line",
       swap(GOAL_LINE, "- goal: Default to water when I forget which habit"), {PLACE})
for value in ("maybe", "not sure yet", "ok"):
    RAN.append(f"fix3 decide asks: {value}")
    text = added(f"- decide: {value}")
    if asks(text) != [("Goal", value)] or failed(text):
        FAILS.append(f"fix3 decide asks: {value}: {asks(text)} {failed(text)}")
for line, want in (("- how: ok", [("Done", "how: ok")]), ("- stated: ok", [("Done", "ok")])):
    RAN.append(f"fix3 a prefix does not hide an ask: {line}")
    if asks(added(line)) != want:
        FAILS.append(f"fix3 a prefix does not hide an ask: {line}: {asks(added(line))}")
expect_exit("fix3 exit 2 on decide: maybe", added("- decide: maybe"), 2)


def expect_unreadable(name, path):
    RAN.append(name)
    got = subprocess.run([sys.executable, SCRIPT, path], capture_output=True, text=True)
    said = (got.stdout + got.stderr).strip().splitlines()
    if got.returncode != 3 or len(said) != 1 or "Traceback" in got.stderr:
        FAILS.append(f"{name}: exit {got.returncode}, said {said}")


expect_unreadable("fix3 a missing path exits 3", os.path.join(tempfile.mkdtemp(), "missing.md"))
expect_unreadable("fix3 a directory exits 3", tempfile.mkdtemp())
BINARY = os.path.join(tempfile.mkdtemp(), "binary.md")
open(BINARY, "wb").write(b"# Decisions\n\xff\xfe\n")
expect_unreadable("fix3 a non-UTF-8 file exits 3", BINARY)

# Invariant: on every text above, the mapper exits as check_decisions does, and a brief it prints passes check_brief.
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outcome", "check")))
import map_decisions  # noqa: E402
from check_brief import ask_lines, check as check_brief  # noqa: E402

for number, text in enumerate(TEXTS):
    path = write(text)
    with contextlib.redirect_stdout(io.StringIO()):
        dec = main(path)
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        mapped = map_decisions.main(path)
    brief = printed.getvalue()
    bad = [] if mapped == dec else [f"mapper exit {mapped}, check_decisions exit {dec}"]
    if mapped == 0:
        bad += [f for _, fails in check_brief(brief) for f in fails] + ask_lines(brief)
    RAN.append(f"invariant {number}")
    if bad:
        FAILS.append(f"invariant {number}: {bad}\n{text}")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
