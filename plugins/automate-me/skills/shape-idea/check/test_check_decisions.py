"""Run: python3 check/test_check_decisions.py"""
import contextlib
import io
import os
import re
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
BRIEF = "the mapped brief passes outcome's brief check"
DECIDED = "Decided values are decisions"


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
for token in ("TBD", "TODO", "n/a", "<the want...>"):
    expect(f"placeholder slot values fail {token}",
           swap("- goal: a tiny habit tracker on my phone", f"- goal: {token}"), {BRIEF})
expect("a slot value that is only punctuation is empty",
       swap("- goal: a tiny habit tracker on my phone", "- goal: ..."), {"slot values are not empty"})
expect("placeholder slot values fail ?",
       swap("- goal: a tiny habit tracker on my phone", "- goal: ?"),
       {DECIDED, "slot values are not empty"})
expect("decided value ending in a question fails",
       swap("- goal: a tiny habit tracker on my phone", "- goal: a tiny habit tracker?"), {DECIDED})
open_tbd = swap("- output: the current streak on the phone\n", "")
open_tbd = swap("- Do you want a reminder?", "- output: TBD?", open_tbd)
open_tbd = swap("- stop: done", "- stop: turn-cap", open_tbd)
open_tbd = swap("- turns: 1", "- turns: 10", open_tbd)
expect("open placeholder slot fails", open_tbd, {QUESTION})
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
expect("evals with a TBD fail case fails", added("- evals: marking today should pass. TBD should fail."), {BRIEF})
expect("evals with only a pass case asks, as check_brief does", added("- evals: pass: mark today"), set())
expect("tools write first none fails", added("- tools: write first: none"), {BRIEF})


def reason(text, check_name):
    return " ".join(fail for name, fails in check(text) if name == check_name for fail in fails)


for label, text, check_name in (
        ("output: unknown", swap("- output: the current streak on the phone", "- output: unknown"), DECIDED),
        ("tools: unknown: X or Y", added("- tools: unknown: waiting to pick Python or Node"), DECIDED),
        ("agents: unknown yet", added("- agents: unknown yet"), DECIDED)):
    expect(f"unknown is not ready: {label}", text, {check_name})
    RAN.append(f"unknown message: {label}")
    if "move it to Open as a question" not in reason(text, check_name):
        FAILS.append(f"unknown message: {label}: {reason(text, check_name)}")
for label, line in (("verify: it looks good", "- verify: it looks good"), ("done: clean", "- done: clean")):
    slot = line[2:line.index(":")]
    old = next(row for row in GOOD.splitlines() if row.startswith(f"- {slot}:"))
    expect(f"trap word slot fails: {label}", swap(old, line), {BRIEF})
for value in ("to be decided", "same as above", "fill in later"):
    expect(f"placeholder phrase fails: {value}",
           swap("- output: the current streak on the phone", f"- output: {value}"), {BRIEF})
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
expect("only the end of an Open item matters",
       swap("- Do you want a reminder?", "- Do you want a reminder? Or a badge?"), set())
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
       swap("- output: ok", "- output: TBD", CONFIRMED).replace("- Output: ok", "- Output: TBD"), {BRIEF})
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
OUT_LINE = "- output: the current streak on the phone"


def out(value):
    return swap(OUT_LINE, f"- output: {value}")


def open_q(line):
    return swap("- Do you want a reminder?", line)


def parked(line):
    return swap("- share streaks with friends", line)


for label, text, check_name, words in (
        ("stated italic unknown output", out("stated: *unknown*"), DECIDED, "move it to Open as a question"),
        ("stated TBD output", out("stated: TBD"), BRIEF, "placeholder"),
        ("italic unknown output", out("_unknown_"), DECIDED, "move it to Open as a question"),
        ("quoted unknown output", out('"unknown"'), DECIDED, "move it to Open as a question"),
        ("paren unknown yet agents", added("- agents: (unknown yet)"), DECIDED, "move it to Open as a question"),
        ("italic unknown tools", added("- tools: *unknown*: Slack or Teams"), DECIDED, "move it to Open as a question"),
        ("italic unknown eval case", added("- evals: pass: *unknown*; fail: a missed day keeps the streak"), DECIDED,
         "move it to Open as a question"),
        ("extra TBD eval case", added("- evals: pass: mark today and the streak goes up; fail: miss a day and it"
                                      " still grows; pass: TBD"), BRIEF, "placeholder"),
        ("other line trap", added("- it should look clean and modern"), BRIEF, "no visible signal"),
        ("other line unknown", added("- unknown: which browser"), DECIDED, "move it to Open as a question"),
        ("other line stated unknown", added("- stated: unknown"), DECIDED, "move it to Open as a question"),
        ("other line stated TBD", added("- stated: TBD"), BRIEF, "placeholder"),
        ("other line question", added("- should a link expire?"), DECIDED, "move it to Open"),
        ("parked unknown", parked("- unknown"), BRIEF, "is not 'unknown: <question>?'"),
        ("parked trap", parked("- clean"), BRIEF, "no visible signal"),
        ("fence under Open", open_q("- Do you want a reminder?\n```\n- sync between phones?\n```"), FENCE, "under Open"),
        ("fence under Parked", parked("- share streaks with friends\n~~~\n- sync between phones, not now\n~~~"), FENCE,
         "under Parked")):
    expect(f"fix3 fails: {label}", text, {check_name})
    RAN.append(f"fix3 message: {label}")
    if words not in reason(text, check_name):
        FAILS.append(f"fix3 message: {label}: {reason(text, check_name)}")

expect("fix3 fails: an Open unknown with no question", open_q("- unknown: ?"), {QUESTION})
expect("fix3 fails: an Open slot unknown with no question", swap(OUT_LINE, "", open_q("- output: unknown: ?")).replace(
    "- stop: done", "- stop: turn-cap").replace("- turns: 1", "- turns: 10"), {QUESTION})

GOAL_LINE = "- goal: a tiny habit tracker on my phone"
for label, text in (
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
expect("r5 passes: default goal without a decide line, since the stock decide question is not in Goal",
       swap(GOAL_LINE, "- goal: Default to water when I forget which habit"), set())
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


# Round 4. An answer whose first word is "unknown" is never ready. Bare, `unknown:`, or the word and punctuation or a
# short tail is a question for Open. Any longer value asks whether it is decided. Only the shape decides, not a word list.
for label, text in (
        ("tools Unknown for now", added("- tools: Unknown for now")),
        ("tools unknown, Slack or Teams", added("- tools: unknown, Slack or Teams")),
        ("output unknown for now", out("unknown for now")),
        ("agents unknown for now", added("- agents: unknown for now")),
        ("decide unknown so far", added("- decide: unknown so far")),
        ("output quoted unknown colon", out('"unknown": CSV or JSON')),
        ("output stated Unknown dash", out("stated: Unknown - CSV or JSON")),
        ("tools unknown parens", added("- tools: unknown (Slack or Teams)")),
        ("tools unknown semicolon", added("- tools: unknown; ask Sam")),
        ("evals unknown case bodies", added("- evals: pass: unknown for now; fail: unknown, ask Sam")),
        ("decided out of scope unknown", added("- out of scope: unknown for now")),
        ("parked out of scope unknown", parked("- out of scope: unknown for now"))):
    expect(f"r4 unknown is a question: {label}", text, {DECIDED})
    RAN.append(f"r4 unknown message: {label}")
    if "move it to Open as a question" not in reason(text, DECIDED):
        FAILS.append(f"r4 unknown message: {label}: {reason(text, DECIDED)}")


def ask_out(text):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(write(text))
    return code, buf.getvalue()


for label, text, slot, value in (
        ("unknown prose in done", swap("- done: mark today done in under 10 seconds",
                                       "- done: unknown file types go to an Other folder"),
         "Done", "unknown file types go to an Other folder"),
        ("Unknown prose in output", out("Unknown senders listed with a count"), "Output",
         "Unknown senders listed with a count"),
        ("unknown-file prose in tools", added("- tools: Unknown-file detector script in tools/"), "Tools",
         "Unknown-file detector script in tools/")):
    expect(f"r4 unknown prose asks: {label}", text, set())
    code, said = ask_out(text)
    RAN.append(f"r4 unknown prose ask line: {label}")
    if code != 2 or f"ASK: {slot}: Is '{value}' decided, or still unknown?" not in said:
        FAILS.append(f"r4 unknown prose ask line: {label}: exit {code}\n{said}")
    RAN.append(f"r4 a Confirmed line lifts the unknown ask: {label}")
    if ask_out(text + f"\n## Confirmed\n\n- {slot}: {value}\n")[0] != 0:
        FAILS.append(f"r4 a Confirmed line lifts the unknown ask: {label}")

expect("r4 an apostrophe inside a quoted label does not end the question",
       open_q("- Should the button say 'What's next?' or 'Continue'?"), set())
expect("r4 a question may end inside a closing quote", open_q('- should the label say "Continue?"'), set())
for label, line in (("tools ?", "- tools: ?"), ("evals TBD?", "- evals: TBD?"), ("agents unknown: ?", "- agents: unknown: ?"),
                    ("decide ?", "- decide: ?"), ("bare hole", "- <question>?")):
    text = open_q(f"- Do you want a reminder?\n{line}")
    expect(f"r4 an Open item that is a placeholder or only a hole fails: {label}", text, {QUESTION})

for label, text, want in (
        ("hole in a non-slot Decided line", added("- the form submits on <Enter>"),
         [("Done", "the form submits on <Enter>")]),
        ("hole in a Parked line", parked("- the form submits on <Enter>"),
         [("Parking lot", "the form submits on <Enter>")]),
        ("unlabeled evals", added("- evals: a poll with 3 choices works and a poll with none errors"),
         [("Evals", "a poll with 3 choices works and a poll with none errors")]),
        ("parked out of scope AI", parked("- out of scope: AI"), [("Constraints", "out of scope: AI")]),
        ("parked bold out of scope AI", parked("- **out of scope:** AI"), [("Constraints", "out of scope: AI")])):
    expect(f"r4 asks, not fails: {label}", text, set())
    RAN.append(f"r4 ask value: {label}")
    if asks(text) != want:
        FAILS.append(f"r4 ask value: {label}: {asks(text)}")

for label, line in (("bold tools", "- **tools:** Slack only"), ("bold decide", "- **decide:** whether to keep the bot"),
                    ("singular tool", "- tool: Slack only"),
                    ("singular eval", "- eval: pass: a poll with 3 choices; fail: a poll with none")):
    expect(f"r4 a loose extra label is still that line: {label}", added(line), set())
    added_twice = added(line + "\n" + line.replace("**", ""))
    expect(f"r4 a loose extra label counts as a repeat: {label}", added_twice, {EXTRA})

# Round 5. One normalization reads an answer's first word: markup, brackets, link syntax and every leading label go
# first. A label with nothing after it fails. `stated:` keeps code spans. An injected line never fails a user's slot.
CHECK_MAP = os.path.normpath(os.path.join(os.path.dirname(SCRIPT), "..", "..", "outcome", "check", "map_decisions.py"))
for label, text in (
        ("paren unknown before a list", out("(unknown), CSV or JSON")),
        ("unknown as link text", out("[unknown](https://example.org/status)")),
        ("bold paren unknown", out("**(unknown)** for now")),
        ("linked unknown tools", added("- tools: [unknown](https://example.org/tools), Slack or Teams")),
        ("compound out of scope stated unknown", added("- out of scope: stated: unknown for now")),
        ("parked compound out of scope stated unknown", parked("- out of scope: stated: unknown for now")),
        ("stated after how", added("- how: stated: unknown")),
        ("full-width parked out of scope unknown", parked("- out of scope：unknown for now"))):
    expect(f"r5 unknown is a question: {label}", text, {DECIDED})
    RAN.append(f"r5 unknown message: {label}")
    if "move it to Open as a question" not in reason(text, DECIDED):
        FAILS.append(f"r5 unknown message: {label}: {reason(text, DECIDED)}")

for label, text, words in (
        ("stated then how clean", added("- stated: how: clean"), "no visible signal"),
        ("how then stated clean", added("- how: stated: clean"), "no visible signal"),
        ("out of scope then stated TBD", added("- out of scope: stated: TBD"), "placeholder")):
    expect(f"r5 compound labels hide nothing: {label}", text, {BRIEF})
    RAN.append(f"r5 compound message: {label}")
    if words not in reason(text, BRIEF):
        FAILS.append(f"r5 compound message: {label}: {reason(text, BRIEF)}")

EMPTY = [("decide stated", added("- decide: stated:")), ("tools stated", added("- tools: stated:")),
         ("agents stated", added("- agents: stated:")), ("evals stated", added("- evals: stated:")),
         ("write first stated", added("- write first: stated:")), ("bold decide bold stated", added("- **decide:** **stated:**")),
         ("code stated decide", added("- decide: `stated:`")), ("other line stated", added("- stated:")),
         ("other line bold stated", added("- **stated:**")), ("out of scope stated", added("- out of scope: stated:")),
         ("output stated", out("stated:")), ("output bold stated", out("**stated:**")),
         ("parked stated", parked("- stated:")), ("parked out of scope stated", parked("- out of scope: stated:")),
         ("goal stated", swap(GOAL_LINE, "- goal: stated:"))]
for label, text in EMPTY:
    RAN.append(f"r5 an empty labelled value fails clearly: {label}")
    said = {}
    for name, script in (("check", SCRIPT), ("map", CHECK_MAP)):
        got = subprocess.run([sys.executable, script, write(text)], capture_output=True, text=True)
        said[name] = got
    bad = [f"{name} exit {got.returncode}" for name, got in said.items() if got.returncode != 1]
    bad += [f"{name} wrote to stderr: {got.stderr[-300:]}" for name, got in said.items() if got.stderr]
    if not re.search(r"(empty value|needs a value|no value)", said["check"].stdout):
        bad.append(f"no empty-value message:\n{said['check'].stdout[-600:]}")
    if bad:
        FAILS.append(f"r5 an empty labelled value fails clearly: {label}: {bad}")

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(SCRIPT), "..", "..", "outcome", "check")))
from map_decisions import map_text as map_brief  # noqa: E402

for label, text, kept in (
        ("stated before a code span", added("- stated: `<col>` is the literal header"), "`<col>` is the literal header"),
        ("bold stated before a code span", added("- **stated:** `<col>` is the literal header"),
         "`<col>` is the literal header"),
        ("stated inside a code span", added("- `stated: <col> is the literal header`"),
         "`<col> is the literal header`"),
        ("parked stated before a command", parked("- stated: run `make check` before a release"),
         "run `make check` before a release")):
    expect(f"r5 stated keeps code spans: {label}", text, set())
    RAN.append(f"r5 stated keeps code spans in the brief: {label}")
    if asks(text) or f"  - {kept}\n" not in map_brief(text):
        FAILS.append(f"r5 stated keeps code spans in the brief: {label}: {asks(text)}\n{map_brief(text)}")

DARK = GOOD.replace(GOAL_LINE, "- goal: default new users to dark mode").replace(
    "- done: mark today done in under 10 seconds", "- done: new accounts open in dark mode")
expect("r5 a goal that starts with default is valid", DARK, set())
expect_exit("r5 a goal that starts with default exits 0", DARK, 0)
OPEN_GOAL = swap(GOAL_LINE, "", added("- decide: default to water on a busy day")).replace(
    "- Do you want a reminder?", "- goal: which habit comes first?\n- Do you want a reminder?").replace(
    "- stop: done", "- stop: turn-cap").replace("- turns: 1", "- turns: 10")
expect("r5 an Open goal beside a decide line that starts with default", OPEN_GOAL, set())

for label, text, slot, value in (
        ("unknown senders get nothing", swap("- constraints: no accounts, it's only me",
                                             "- constraints: unknown senders get nothing"),
         "Constraints", "unknown senders get nothing"),
        ("unknown at the moment", out("unknown at the moment"), "Output", "unknown at the moment")):
    expect(f"r5 a 3-word unknown asks: {label}", text, set())
    code, said = ask_out(text)
    RAN.append(f"r5 a 3-word unknown ask line: {label}")
    if code != 2 or f"ASK: {slot}: Is '{value}' decided, or still unknown?" not in said:
        FAILS.append(f"r5 a 3-word unknown ask line: {label}: exit {code}\n{said}")
    RAN.append(f"r5 a Confirmed line lifts the 3-word unknown: {label}")
    if ask_out(text + f"\n## Confirmed\n\n- {slot}: {value}\n")[0] != 0:
        FAILS.append(f"r5 a Confirmed line lifts the 3-word unknown: {label}")
for label, text in (("unknown until Friday", out("unknown until Friday")), ("unknown so far", out("unknown so far"))):
    expect(f"r5 unknown and two words is a question: {label}", text, {DECIDED})

for label, line, question in (
        ("hole in an Open question", "- Should it press <Enter> to confirm each move?",
         "Should it press <Enter> to confirm each move?"),
        ("hole in an Open tools question", "- tools: Should the poll run in <channel>?",
         "Should the poll run in <channel>?")):
    text = open_q(f"- Do you want a reminder?\n{line}")
    expect(f"r5 an Open hole asks: {label}", text, set())
    code, said = ask_out(text)
    RAN.append(f"r5 an Open hole ask line: {label}")
    if code != 2 or f"ASK: Unknowns: Is '{question}' a real question, or a hole to fill?" not in said:
        FAILS.append(f"r5 an Open hole ask line: {label}: exit {code}\n{said}")
    RAN.append(f"r5 a Confirmed line lifts the Open hole: {label}")
    if ask_out(text + f"\n## Confirmed\n\n- Unknowns: {question}\n")[0] != 0:
        FAILS.append(f"r5 a Confirmed line lifts the Open hole: {label}")

for args in ([], ["a.md", "b.md"]):
    for name, script in (("check", SCRIPT), ("map", CHECK_MAP)):
        RAN.append(f"r5 usage error is one stderr line: {name} {args}")
        got = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
        if got.returncode != 3 or got.stdout or len(got.stderr.strip().splitlines()) != 1:
            FAILS.append(f"r5 usage error is one stderr line: {name} {args}: exit {got.returncode}, "
                         f"{len(got.stdout.splitlines())} stdout lines, stderr {got.stderr!r}")
RAN.append("r5 help with an extra argument is a usage error")
got = subprocess.run([sys.executable, CHECK_MAP, "-h", "x"], capture_output=True, text=True)
if got.returncode != 3:
    FAILS.append(f"r5 help with an extra argument is a usage error: exit {got.returncode}")

for label, text in (("closing quote", out('"the winner only, or the full tally?"')),
                    ("closing bracket", out("(a list or a page?)")),
                    ("full-width mark", out("勝者だけ、それとも全票？")),
                    *((f"mark {mark!r}", out(f"a list or a page{mark}")) for mark in "؟;⁇⁈⁉﹖")):
    expect(f"r6 a Decided question fails: {label}", text, {DECIDED})
    RAN.append(f"r6 a Decided question message: {label}")
    if "move it to Open" not in reason(text, DECIDED):
        FAILS.append(f"r6 a Decided question message: {label}: {reason(text, DECIDED)}")
expect("r6 an opening question mark is not a question", out("¿a list or a page"), set())
for line in ("- 投票は20分で締め切る？", "- Should the button say 'What's next?' or 'Continue'?",
             "- is it a list (or a page?)", "- 結果は「一覧？」"):
    expect(f"r6 an Open question passes: {line}", open_q(line), set())

for label, text in (("deadline", added("- deadline: unknown")), ("tools sub-label", added("- tools: chat API: unknown")),
                    ("agents sub-label", added("- agents: reviewer: unknown")), ("output sub-label", out("status: unknown")),
                    ("bold sub-label", out("**status:** unknown for now"))):
    expect(f"r6 an unknown after the last label fails: {label}", text, {DECIDED})
for label, text in (("url", out("https://unknown.example.org/status")),
                    ("code span", out("`status: unknown` is the literal header")),
                    ("time", added("- the poll closes at 9:30"))):
    expect(f"r6 a colon that is not a label stays: {label}", text, set())

DOTLESS = swap("## Decided", "## Decıded")
for name, script in (("check", SCRIPT), ("map", CHECK_MAP)):
    RAN.append(f"r6 an unmapped heading is a usage error: {name}")
    got = subprocess.run([sys.executable, script, write(DOTLESS)], capture_output=True, text=True)
    if got.returncode != 3 or got.stdout or len(got.stderr.strip().splitlines()) != 1 or "Traceback" in got.stderr:
        FAILS.append(f"r6 an unmapped heading is a usage error: {name}: exit {got.returncode}, stderr {got.stderr[-300:]!r}")

for question in ("out of scope: a watch app, or later?", "out of scope: a watch app？"):
    text = parked(f"- {question}")
    expect(f"r6 a Parked out-of-scope question passes: {question}", text, set())
    brief = map_brief(text)
    RAN.append(f"r6 a Parked out-of-scope question stays a question: {question}")
    if f"  - {question}\n" in brief.split("- Tools", 1)[0] or f"unknown: {question[:-1]}?" not in brief:
        FAILS.append(f"r6 a Parked out-of-scope question stays a question: {question}\n{brief}")

CHECKER = open(SCRIPT, encoding="utf-8").read()
RAN.append("r4 docstring names the map line")
if "map:" not in CHECKER.split('"""', 2)[1].split("Fails (exit 1) when:", 1)[1].split("Asks (exit 2", 1)[0]:
    FAILS.append("r4 docstring names the map line")


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
