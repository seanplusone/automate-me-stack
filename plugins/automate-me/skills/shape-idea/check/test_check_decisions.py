"""Run: python3 check/test_check_decisions.py"""
import contextlib
import io
import os
import re
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
QUESTION = "no open item is a placeholder"
STOP = "stop reason is done, turn-cap, or open-cap"
TURNS = "turn count recorded and at most 10"
SLOTS = "every slot is decided or open"
DONE = "stop matches the file"
MATCH = "stop matches the file"
ONE_LINE = "no item longer than one line"
NEXT = "handoff names outcome"
WRITING = "handoff says writing pass"
BRIEF = "the mapped brief passes outcome's brief check"
VALUES = "no value is a placeholder or template text"


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


def write(text, confirmed=None):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "decisions.md")
    open(path, "w", encoding="utf-8").write(text)
    if confirmed is not None:
        open(os.path.join(folder, "confirmed.md"), "w", encoding="utf-8").write(confirmed)
    return path


def ask_out(text, confirmed=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(write(text, confirmed))
    return code, buf.getvalue()


def asks(text, confirmed=None):
    """(slot, value) for each CHECK WITH ME item that main() prints."""
    said = ask_out(text, confirmed)[1]
    return [(m.group(1), m.group(2)) for m in re.finditer(r'^- ([^:\n]+): "(.*)"$', said.split("CHECK WITH ME (", 1)[-1], re.M)
            if "CHECK WITH ME (" in said]


def expect_me(name, text, slot, value, words=None):
    """Format valid, exit 2, and the value is in the CHECK WITH ME list. A yes in confirmed.md clears it."""
    expect(name, text, set())
    RAN.append(f"{name}: check with me")
    code, said = ask_out(text)
    if code != 2 or (slot, value) not in asks(text) or (words and words not in said):
        FAILS.append(f"{name}: check with me: exit {code}, {asks(text)}\n{said[-500:]}")
    RAN.append(f"{name}: a yes clears it")
    confirmed = "".join(f"- {s}: {v} | yes\n" for s, v in asks(text))
    if ask_out(text, confirmed)[0] != 0:
        FAILS.append(f"{name}: a yes clears it: {ask_out(text, confirmed)[1][-500:]}")


def opens(n):
    lines = "\n".join(f"- Open question {i}?" for i in range(1, n + 1))
    return swap("- Do you want a reminder?", lines)


def missing_slot(line):
    text = swap(line, "")
    text = swap("- stop: done", "- stop: turn-cap", text)
    return swap("- turns: 1", "- turns: 10", text)


expect("good file passes", GOOD, set())
expect("missing Handoff", swap(HANDOFF, ""), {PRESENT})
expect_me("a question mark anywhere makes an Open item a question", swap("- Do you want a reminder?", "- reminders are not settled"),
          "Unknowns", "reminders are not settled")
expect("question mark not at the end", swap("- Do you want a reminder?", "- Do you want a reminder? Maybe."), set())
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
           swap("- goal: a tiny habit tracker on my phone", f"- goal: {token}"), {VALUES})
expect("a slot value that is only punctuation is empty",
       swap("- goal: a tiny habit tracker on my phone", "- goal: ..."), {"slot values are not empty"})
expect("placeholder slot values fail ?",
       swap("- goal: a tiny habit tracker on my phone", "- goal: ?"),
       {"slot values are not empty"})
expect_me("decided value with a question mark is checked with me",
          swap("- goal: a tiny habit tracker on my phone", "- goal: a tiny habit tracker?"), "Goal", "a tiny habit tracker?")
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
expect_me("none is checked with me, not failed", added("- tools: write first: none"), "Tools", "write first: none")


def reason(text, check_name):
    return " ".join(fail for name, fails in check(text) if name == check_name for fail in fails)


# Any word "unknown" in a Decided value is checked with the person. A yes in confirmed.md clears it.
for label, text, slot, value in (
        ("output: unknown", swap("- output: the current streak on the phone", "- output: unknown"), "Output", "unknown"),
        ("tools: unknown: X or Y", added("- tools: unknown: waiting to pick Python or Node"), "Tools",
         "unknown: waiting to pick Python or Node"),
        ("agents: unknown yet", added("- agents: unknown yet"), "Agents and roles", "unknown yet")):
    expect_me(f"unknown is checked with me: {label}", text, slot, value, "Open")
for label, line, slot, value in (("verify: it looks good", "- verify: it looks good", "Verification", "it looks good"),
                                 ("done: clean", "- done: clean", "Done", "clean")):
    old = next(row for row in GOOD.splitlines() if row.startswith(line[:line.index(":") + 1]))
    expect_me(f"trap word slot is checked with me: {label}", swap(old, line), slot, value)
for value in ("to be decided", "same as above", "fill in later"):
    expect(f"placeholder phrase fails: {value}",
           swap("- output: the current streak on the phone", f"- output: {value}"), {VALUES})
expect_me("a hedge is checked with me", swap("- output: the current streak on the phone", "- output: not sure yet"),
          "Output", "not sure yet")
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

# A value check_brief would ask about is in the CHECK WITH ME list, not a ready line.
OK_OUT = swap("- output: the current streak on the phone", "- output: ok")
expect_me("a short value is checked with me", OK_OUT, "Output", "ok")
RAN.append("check with me on an evals case body")
if ("Evals", "ok") not in asks(added("- evals: pass: ok; fail: a missed day keeps the streak")):
    FAILS.append(f"check with me on an evals case body: {asks(added('- evals: pass: ok; fail: a missed day keeps the streak'))}")
expect_me("another Decided line lands in Done", swap(HABIT, "- maybe"), "Done", "maybe")
CONFIRMED = "- Output: ok | yes\n"
RAN.append("a confirmation never lifts a format error")
if ask_out(swap("- output: ok", "- output: TBD", OK_OUT), "- Output: TBD | yes\n")[0] != 1:
    FAILS.append("a confirmation never lifts a format error")
RAN.append("a confirmed.md line that is not `- <Slot>: <value> | <answer>` is a format error")
if ask_out(OK_OUT, "- Output ok yes\n")[0] != 1:
    FAILS.append("a confirmed.md line that is not `- <Slot>: <value> | <answer>` is a format error")
RAN.append("a Confirmed section in decisions.md is gone: confirmations live in confirmed.md")
if ask_out(OK_OUT + "\n## Confirmed\n\n- Output: ok\n")[0] != 1:
    FAILS.append("a Confirmed section in decisions.md is gone")


def expect_exit(name, text, code, confirmed=None):
    RAN.append(name)
    got, said = ask_out(text, confirmed)
    if got != code:
        FAILS.append(f"{name}: exit {got}, wanted {code}\n{said}")


expect_exit("exit 0 on a good file", GOOD, 0)
expect_exit("exit 1 on a bad file", swap(HANDOFF, ""), 1)
expect_exit("exit 2 on a value to confirm", OK_OUT, 2)
expect_exit("exit 0 once confirmed", OK_OUT, 0, CONFIRMED)
expect_exit("exit 1 beats check with me", swap(HANDOFF, "", OK_OUT), 1)
expect_exit("a UTF-8 BOM is not text", "﻿" + GOOD, 0)
RAN.append("check with me format")
said = ask_out(OK_OUT)[1]
if ('CHECK WITH ME (1)\n- Output: "ok"\n  Why: ' not in said or "\n  Suggest: " not in said
        or "CHECK WITH ME decisions:" not in said):
    FAILS.append(f"check with me format: {said}")

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_decisions.py")


def expect_code(name, args, code):
    RAN.append(name)
    got = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True)
    if got.returncode != code:
        FAILS.append(f"{name}: exit {got.returncode}, wanted {code}")


expect_code("usage exits 3", [], 3)
expect_code("help exits 0", ["--help"], 0)

# Every Decided line is judged by the same rules, whatever its label or prefix.
OUT_LINE = "- output: the current streak on the phone"


def out(value):
    return swap(OUT_LINE, f"- output: {value}")


def open_q(line):
    return swap("- Do you want a reminder?", line)


def parked(line):
    return swap("- share streaks with friends", line)


for label, text, slot, value in (
        ("stated italic unknown output", out("stated: *unknown*"), "Output", "*unknown*"),
        ("italic unknown output", out("_unknown_"), "Output", "_unknown_"),
        ("quoted unknown output", out('"unknown"'), "Output", '"unknown"'),
        ("paren unknown yet agents", added("- agents: (unknown yet)"), "Agents and roles", "(unknown yet)"),
        ("italic unknown tools", added("- tools: *unknown*: Slack or Teams"), "Tools", "*unknown*: Slack or Teams"),
        ("italic unknown eval case", added("- evals: pass: *unknown*; fail: a missed day keeps the streak"), "Evals",
         "pass: *unknown*; fail: a missed day keeps the streak"),
        ("other line trap", added("- it should look clean and modern"), "Done", "it should look clean and modern"),
        ("other line unknown", added("- unknown: which browser"), "Done", "unknown: which browser"),
        ("other line stated unknown", added("- stated: unknown"), "Done", "unknown"),
        ("other line question", added("- should a link expire?"), "Done", "should a link expire?")):
    expect_me(f"fix3 checked with me: {label}", text, slot, value)

for label, text, check_name, words in (
        ("stated TBD output", out("stated: TBD"), VALUES, "placeholder"),
        ("extra TBD eval case", added("- evals: pass: mark today and the streak goes up; fail: miss a day and it"
                                      " still grows; pass: TBD"), BRIEF, "placeholder"),
        ("other line stated TBD", added("- stated: TBD"), VALUES, "placeholder"),
        ("fence under Open", open_q("- Do you want a reminder?\n```\n- sync between phones?\n```"), FENCE, "under Open"),
        ("fence under Parked", parked("- share streaks with friends\n~~~\n- sync between phones, not now\n~~~"), FENCE,
         "under Parked")):
    expect(f"fix3 fails: {label}", text, {check_name})
    RAN.append(f"fix3 message: {label}")
    if words not in reason(text, check_name):
        FAILS.append(f"fix3 message: {label}: {reason(text, check_name)}")

expect("fix3 a Parked unknown is kept for later", parked("- unknown"), set())
expect("fix3 a Parked trap word is kept for later", parked("- clean"), set())
expect("fix3 fails: an Open unknown with no question", open_q("- unknown: ?"), {QUESTION})
expect("fix3 fails: an Open slot unknown with no question", swap(OUT_LINE, "", open_q("- output: unknown: ?")).replace(
    "- stop: done", "- stop: turn-cap").replace("- turns: 1", "- turns: 10"), {"slot values are not empty"})

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
    expect_exit(f"fix3 passes with exit 0: {label}", text, 0)

expect("fix3 a curly quoted label is not a second question, though the writing check bans curly quotes",
       open_q("- Should the button say ‘Vote?’ or ‘Pick’?"), {"prose passes the writing check"})
expect("r5 passes: default goal without a decide line, since the stock decide question is not in Goal",
       swap(GOAL_LINE, "- goal: Default to water when I forget which habit"), set())
for value in ("maybe", "not sure yet", "ok"):
    expect_me(f"fix3 decide is checked with me: {value}", added(f"- decide: {value}"), "Goal", value)
for line, slot, value in (("- how: ok", "Done", "how: ok"), ("- stated: ok", "Done", "ok")):
    expect_me(f"fix3 a prefix does not hide a value: {line}", added(line), slot, value)


# Any value with "unknown" in it is checked with the person: no shape rule, no word list.
for label, text, slot, value in (
        ("tools Unknown for now", added("- tools: Unknown for now"), "Tools", "Unknown for now"),
        ("tools unknown, Slack or Teams", added("- tools: unknown, Slack or Teams"), "Tools", "unknown, Slack or Teams"),
        ("output unknown for now", out("unknown for now"), "Output", "unknown for now"),
        ("decide unknown so far", added("- decide: unknown so far"), "Goal", "unknown so far"),
        ("output quoted unknown colon", out('"unknown": CSV or JSON'), "Output", '"unknown": CSV or JSON'),
        ("output stated Unknown dash", out("stated: Unknown - CSV or JSON"), "Output", "Unknown - CSV or JSON"),
        ("tools unknown parens", added("- tools: unknown (Slack or Teams)"), "Tools", "unknown (Slack or Teams)"),
        ("evals unknown case bodies", added("- evals: pass: unknown for now; fail: unknown, ask Sam"), "Evals",
         "pass: unknown for now; fail: unknown, ask Sam"),
        ("decided out of scope unknown", added("- out of scope: unknown for now"), "Constraints",
         "out of scope: unknown for now"),
        ("parked out of scope unknown", parked("- out of scope: unknown for now"), "Constraints",
         "out of scope: unknown for now"),
        ("unknown prose in done", swap("- done: mark today done in under 10 seconds",
                                       "- done: unknown file types go to an Other folder"),
         "Done", "unknown file types go to an Other folder"),
        ("Unknown-file prose in tools", added("- tools: Unknown-file detector script in tools/"), "Tools",
         "Unknown-file detector script in tools/"),
        ("paren unknown before a list", out("(unknown), CSV or JSON"), "Output", "(unknown), CSV or JSON"),
        ("unknown as link text", out("[unknown](https://example.org/status)"), "Output",
         "[unknown](https://example.org/status)"),
        ("compound out of scope stated unknown", added("- out of scope: stated: unknown for now"), "Constraints",
         "out of scope: unknown for now"),
        ("stated after how", added("- how: stated: unknown"), "Done", "how: unknown"),
        ("full-width parked out of scope unknown", parked("- out of scope：unknown for now"), "Constraints",
         "out of scope: unknown for now"),
        ("unknown senders get nothing", swap("- constraints: no accounts, it's only me",
                                             "- constraints: unknown senders get nothing"),
         "Constraints", "unknown senders get nothing"),
        ("unknown until Friday", out("unknown until Friday"), "Output", "unknown until Friday"),
        ("deadline", added("- deadline: unknown"), "Done", "deadline: unknown"),
        ("tools sub-label", added("- tools: chat API: unknown"), "Tools", "chat API: unknown"),
        ("bold sub-label", out("**status:** unknown for now"), "Output", "**status:** unknown for now"),
        ("url", out("https://unknown.example.org/status"), "Output", "https://unknown.example.org/status"),
        ("code span", out("`status: unknown` is the literal header"), "Output", "`status: unknown` is the literal header")):
    expect_me(f"r4 unknown is checked with me: {label}", text, slot, value)

expect("r4 an apostrophe inside a quoted label does not end the question",
       open_q("- Should the button say 'What's next?' or 'Continue'?"), set())
expect("r4 a question may end inside a closing quote", open_q('- should the label say "Continue?"'), set())
for label, line in (("tools ?", "- tools: ?"), ("evals TBD?", "- evals: TBD?"), ("agents unknown: ?", "- agents: unknown: ?"),
                    ("decide ?", "- decide: ?"), ("bare hole", "- <question>?")):
    text = open_q(f"- Do you want a reminder?\n{line}")
    expect(f"r4 an Open item that is a placeholder or only a hole fails: {label}", text, {QUESTION})

for label, text, slot, value in (
        ("hole in a non-slot Decided line", added("- the form submits on <Enter>"), "Done", "the form submits on <Enter>"),
        ("hole in a Parked line", parked("- the form submits on <Enter>"), "Parking lot", "the form submits on <Enter>"),
        ("parked out of scope AI", parked("- out of scope: AI"), "Constraints", "out of scope: AI"),
        ("parked bold out of scope AI", parked("- **out of scope:** AI"), "Constraints", "out of scope: AI"),
        ("hole in an Open question", open_q("- Should it press <Enter> to confirm each move?"), "Unknowns",
         "Should it press <Enter> to confirm each move?"),
        ("hole in an Open tools question", open_q("- Do you want a reminder?\n- tools: Should the poll run in <channel>?"),
         "Unknowns", "Should the poll run in <channel>?")):
    expect_me(f"r4 checked with me, not failed: {label}", text, slot, value)

UNLABELED = added("- evals: a poll with 3 choices works and a poll with none errors")
RAN.append("r4 unlabeled evals are checked with me, and only labels clear them")
if (asks(UNLABELED) != [("Evals", "a poll with 3 choices works and a poll with none errors")]
        or ask_out(UNLABELED, "- Evals: a poll with 3 choices works and a poll with none errors | yes\n")[0] != 2):
    FAILS.append(f"r4 unlabeled evals are checked with me, and only labels clear them: {asks(UNLABELED)}")

for label, line in (("bold tools", "- **tools:** Slack only"), ("bold decide", "- **decide:** whether to keep the bot"),
                    ("singular tool", "- tool: Slack only"),
                    ("singular eval", "- eval: pass: a poll with 3 choices; fail: a poll with none")):
    expect(f"r4 a loose extra label is still that line: {label}", added(line), set())
    added_twice = added(line + "\n" + line.replace("**", ""))
    expect(f"r4 a loose extra label counts as a repeat: {label}", added_twice, {EXTRA})

# A label with nothing after it fails. `stated:` keeps code spans. An injected line never fails a user's slot.
CHECK_MAP = os.path.normpath(os.path.join(os.path.dirname(SCRIPT), "..", "..", "outcome", "check", "map_decisions.py"))
for label, text in (
        ("stated then how clean", added("- stated: how: clean")),
        ("how then stated clean", added("- how: stated: clean"))):
    expect_me(f"r5 compound labels hide nothing: {label}", text, "Done", "how: clean")
expect("r5 compound labels hide nothing: out of scope then stated TBD", added("- out of scope: stated: TBD"), {VALUES})

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

for args in ([], ["a.md", "b.md"], ["a.md", "--confirmed"]):
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

# Any question mark in a Decided value, of any script, is checked with the person.
for label, value in (("closing quote", '"the winner only, or the full tally?"'),
                     ("closing bracket", "(a list or a page?)"),
                     ("full-width mark", "勝者だけ、それとも全票？"),
                     ("bold", "**CSV or JSON?**"),
                     ("quoted question", 'a Slack message that asks "Who\'s in for lunch?"'),
                     ("opening mark", "¿a list or a page"),
                     *((f"mark {mark!r}", f"a list or a page{mark}") for mark in "\u061f\u037e\u2047\u2048\u2049\ufe56")):
    expect_me(f"r6 a Decided question mark is checked with me: {label}", out(value), "Output", value)
for line in ("- 投票は20分で締め切る？", "- Should the button say 'What's next?' or 'Continue'?",
             "- is it a list (or a page?)", "- 結果は「一覧？」", "- **Should the poll close after 20 minutes?**"):
    expect(f"r6 an Open question passes: {line}", open_q(line), set())
    expect_exit(f"r6 an Open question exits 0: {line}", open_q(line), 0)
expect("r6 a colon that is not a label stays: time", added("- the poll closes at 9:30"), set())
expect_exit("r6 a colon that is not a label exits 0: time", added("- the poll closes at 9:30"), 0)

for label, text in (("Decided heading", swap("## Decided", "## Decıded")),
                    ("writing field", swap("- writing: pass", "- wrıting: pass"))):
    for name, script in (("check", SCRIPT), ("map", CHECK_MAP)):
        RAN.append(f"r6 a dotless i is a plain format error: {label}: {name}")
        got = subprocess.run([sys.executable, script, write(text)], capture_output=True, text=True)
        if got.returncode != 1 or "Traceback" in got.stderr + got.stdout:
            FAILS.append(f"r6 a dotless i is a plain format error: {label}: {name}: exit {got.returncode}, "
                         f"stderr {got.stderr[-300:]!r}")

for question in ("out of scope: a watch app, or later?", "out of scope: a watch app？"):
    text = parked(f"- {question}")
    expect_me(f"r6 a Parked out-of-scope question is checked with me: {question}", text, "Parking lot", question)
    brief = map_brief(text)
    RAN.append(f"r6 a Parked out-of-scope question stays a question: {question}")
    if question in brief.split("- Tools", 1)[0] or f"unknown: {question[:-1]}" not in brief:
        FAILS.append(f"r6 a Parked out-of-scope question stays a question: {question}\n{brief}")

CHECKER = open(SCRIPT, encoding="utf-8").read()
RAN.append("r4 docstring names the map line")
DOC = CHECKER.split('"""', 2)[1]
if "map:" not in (DOC + "Format invalid (exit 1) when:").split("Format invalid (exit 1) when:", 1)[1].split("Check with me (exit 2", 1)[0]:
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
