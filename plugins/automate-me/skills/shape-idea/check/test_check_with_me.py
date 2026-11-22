"""Run: python3 check/test_check_with_me.py

The check has three outcomes. Format invalid (exit 1) is only what the script knows for certain. Everything it cannot
be sure about is one CHECK WITH ME list (exit 2). A yes in confirmed.md clears an item, never a format error. The
mapper prints a brief only on exit 0, and that brief passes check_brief.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.normpath(os.path.join(HERE, "..", ".."))
CHECK = os.path.join(HERE, "check_decisions.py")
MAP = os.path.join(SKILLS, "outcome", "check", "map_decisions.py")
BRIEF = os.path.join(SKILLS, "outcome", "check", "check_brief.py")
WRITING = os.path.join(SKILLS, "shared", "check_writing.py")
CASES = os.path.join(SKILLS, "shape-idea", "cases")

FAILS, RAN, SAID = [], [], []

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
OUT_LINE = "- output: the current streak on the phone"
HABIT = "- the one habit is drinking water"


def swap(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new, 1)


def out(value):
    return swap(OUT_LINE, f"- output: {value}")


def added(line):
    return swap(HABIT, f"{HABIT}\n{line}")


def write(text, confirmed=None):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if confirmed is not None:
        with open(os.path.join(folder, "confirmed.md"), "w", encoding="utf-8") as handle:
            handle.write(confirmed)
    return path


def run(script, *args):
    got = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
    return got.returncode, got.stdout, got.stderr


def items(said):
    """(slot, value, why, suggest) for each item in the CHECK WITH ME section."""
    found, lines = [], said.splitlines()
    start = next((i for i, line in enumerate(lines) if re.match(r"^CHECK WITH ME \(\d+\)$", line)), None)
    if start is None:
        return found
    for i in range(start + 1, len(lines)):
        head = re.match(r'^- (?P<slot>[^:]+): "(?P<value>.*)"$', lines[i])
        if head:
            why = lines[i + 1].strip() if i + 1 < len(lines) else ""
            suggest = lines[i + 2].strip() if i + 2 < len(lines) else ""
            found.append((head["slot"], head["value"], why[len("Why: "):] if why.startswith("Why: ") else None,
                          suggest[len("Suggest: "):] if suggest.startswith("Suggest: ") else None))
    return found


def fail(name, why):
    FAILS.append(f"{name}: {why}")


def brief_passes(brief):
    path = os.path.join(tempfile.mkdtemp(), "brief.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(brief)
    return run(BRIEF, path)


def expect_with_me(name, text, slot, value):
    """Exit 2 from both scripts, no brief, the item listed with a Why and a Suggest. A yes clears it, and then the mapped
    brief passes check_brief."""
    RAN.append(name)
    path = write(text)
    code, said, err = run(CHECK, path)
    mcode, mapped, merr = run(MAP, path)
    SAID.append(said)
    got = items(said)
    mine = [item for item in got if item[:2] == (slot, value)]
    bad = []
    if code != 2 or mcode != 2:
        bad.append(f"exit {code}, mapper {mcode}, wanted 2")
    if "# Brief" in mapped:
        bad.append("mapper printed a brief")
    if not mine:
        bad.append(f"no item {slot}: {value!r} in {got}")
    elif not mine[0][2] or not mine[0][3]:
        bad.append(f"item has no Why or no Suggest: {mine[0]}")
    if err or merr:
        bad.append(f"stderr {err[-200:]!r} {merr[-200:]!r}")
    confirmed = "".join(f"- {s}: {v} | yes\n" for s, v, _, _ in got)
    path = write(text, confirmed)
    code, said, _ = run(CHECK, path)
    mcode, brief, _ = run(MAP, path)
    if code != 0 or mcode != 0:
        bad.append(f"after confirming every item: exit {code}, mapper {mcode}\n{said[-600:]}")
    else:
        bcode, bsaid, _ = brief_passes(brief)
        if bcode != 0:
            bad.append(f"mapped brief does not pass check_brief: exit {bcode}\n{bsaid[-600:]}")
    if bad:
        fail(name, "; ".join(bad) + f"\n{said[-800:]}")
    return brief if not bad else ""


# 1. The old review blockers land in CHECK WITH ME: never ready, never a wrong fail.
for label, text, slot, value in (
        ("go-live date unknown", added("- go-live date: unknown"), "Done", "go-live date: unknown"),
        ("file format unknown", out("file format (CSV/JSON): unknown"), "Output", "file format (CSV/JSON): unknown"),
        ("tools Node version unknown", added("- tools: Node.js version: unknown"), "Tools", "Node.js version: unknown"),
        ("linked label unknown", out("[format](https://example.org/spec): unknown"), "Output",
         "[format](https://example.org/spec): unknown"),
        ("no space after colon", out("format:unknown"), "Output", "format:unknown"),
        ("agents reviewer unknown", added("- agents: on-call reviewer: unknown"), "Agents and roles",
         "on-call reviewer: unknown"),
        ("bold question", out("**CSV or JSON?**"), "Output", "**CSV or JSON?**"),
        ("quoted question", out('a Slack message that asks "Who\'s in for lunch?"'), "Output",
         'a Slack message that asks "Who\'s in for lunch?"'),
        ("quoted question column", out('a CSV column named "Are you attending?"'), "Output",
         'a CSV column named "Are you attending?"'),
        ("full-width question", out("勝者だけ、それとも全票？"), "Output", "勝者だけ、それとも全票？"),
        ("unknown prose", out("the page shows Status: Unknown"), "Output", "the page shows Status: Unknown"),
        ("unknown senders", swap("- constraints: no accounts, it's only me", "- constraints: reply to: unknown senders"),
         "Constraints", "reply to: unknown senders"),
        ("still unknown", out("still unknown"), "Output", "still unknown"),
        ("hedge", out("maybe a CSV"), "Output", "maybe a CSV"),
        ("hedge not sure", out("a CSV, not sure"), "Output", "a CSV, not sure"),
        ("trap word", swap("- verify: mark today once and read the streak", "- verify: it looks good"), "Verification",
         "it looks good"),
        ("trap word in Done", added("- it should look clean and modern"), "Done", "it should look clean and modern"),
        ("short value", out("ok"), "Output", "ok"),
        ("hole inside a value", added("- the form submits on <Enter>"), "Done", "the form submits on <Enter>"),
        ("decided unknown", out("unknown"), "Output", "unknown"),
        ("nested stated unknown", added("- stated: how: out of scope: maybe"), "Done", "how: out of scope: maybe"),
        ("open without a question", swap("- Do you want a reminder?", "- reminders are not settled"), "Unknowns",
         "reminders are not settled"),
        ("open hole", swap("- Do you want a reminder?", "- Should it press <Enter> to confirm?"), "Unknowns",
         "Should it press <Enter> to confirm?"),
        ("parked out of scope question", swap("- share streaks with friends",
                                              "- out of scope: **Should dietary tags be excluded?**"),
         "Parking lot", "out of scope: **Should dietary tags be excluded?**")):
    expect_with_me(f"check with me: {label}", text, slot, value)

brief = expect_with_me("parked out of scope question stays a question once confirmed",
                       swap("- share streaks with friends", "- out of scope: **Should dietary tags be excluded?**"),
                       "Parking lot", "out of scope: **Should dietary tags be excluded?**")
if brief and "dietary" in brief.split("- Constraints:", 1)[1].split("- Tools:", 1)[0]:
    fail("parked out of scope question stays a question once confirmed", f"it became a Constraint\n{brief}")

# An Evals line with no pass case and fail case is checked with the person. Only labelling the cases clears it, since
# check_brief asks about it whatever the Confirmed block says.
RAN.append("evals with no labelled cases")
EVALS_TEXT = added("- evals: a poll with 3 choices works and a poll with none errors")
code, said, _ = run(CHECK, write(EVALS_TEXT))
SAID.append(said)
again, _, _ = run(CHECK, write(EVALS_TEXT, "- Evals: a poll with 3 choices works and a poll with none errors | yes\n"))
labelled, _, _ = run(CHECK, write(added("- evals: pass: a poll with 3 choices works; fail: a poll with none errors")))
if (code, again, labelled) != (2, 2, 0) or not any(item[0] == "Evals" and item[3] for item in items(said)):
    fail("evals with no labelled cases", f"exits {code}, {again}, {labelled}\n{said[-600:]}")

# 2. An Open question in markup is a question: it passes or is checked with the person, never a format fail.
for line in ("- **Should the poll close after 20 minutes?**", "- 投票は20分で締め切る？",
             "- Should the button say 'What's next?' or 'Continue'?"):
    RAN.append(f"open question is never a format fail: {line}")
    code, said, _ = run(CHECK, write(swap("- Do you want a reminder?", line)))
    mcode, brief, _ = run(MAP, write(swap("- Do you want a reminder?", line)))
    if code not in (0, 2) or mcode != code:
        fail(f"open question is never a format fail: {line}", f"exit {code}, mapper {mcode}\n{said[-600:]}")
    elif code == 0 and brief_passes(brief)[0] != 0:
        fail(f"open question is never a format fail: {line}", f"brief fails check_brief\n{brief}")

# 3. Format invalid: only what the script knows for certain.
for label, text in (("TBD", out("TBD")), ("template hole", out("<goal>")), ("N/A", out("N/A")),
                    ("to be decided", out("to be decided")),
                    ("untouched template slot", swap("- goal: a tiny habit tracker on my phone",
                                                     "- goal: <the want, in the user's words for numbers and names>")),
                    ("untouched template line", added("- <any other firm choice>")),
                    ("open placeholder", swap("- Do you want a reminder?", "- TBD?")),
                    ("missing writing", swap("- writing: pass\n", "")),
                    ("unclosed fence", added("```")),
                    ("missing title", swap("# Decisions: water habit", "# Notes"))):
    RAN.append(f"format invalid: {label}")
    code, said, err = run(CHECK, write(text))
    mcode, mapped, _ = run(MAP, write(text))
    if code != 1 or mcode != 1 or "# Brief" in mapped or err:
        fail(f"format invalid: {label}", f"exit {code}, mapper {mcode}, stderr {err[-200:]!r}\n{said[-600:]}")

# 4. A blank slot is format invalid and also listed with a suggestion.
for label, text, slot in (("blank output", out(""), "Output"), ("blank stated output", out("stated:"), "Output"),
                          ("blank goal", swap("- goal: a tiny habit tracker on my phone", "- goal:"), "Goal")):
    RAN.append(f"blank slot: {label}")
    code, said, _ = run(CHECK, write(text))
    SAID.append(said)
    got = [item for item in items(said) if item[0] == slot]
    if code != 1 or not got or not got[0][3]:
        fail(f"blank slot: {label}", f"exit {code}, items {items(said)}\n{said[-600:]}")

# 5. A confirmation never clears a format error, and a stale one is a note.
RAN.append("a confirmation never clears a format error")
code, said, _ = run(CHECK, write(out("TBD"), "- Output: TBD | yes\n"))
if code != 1:
    fail("a confirmation never clears a format error", f"exit {code}\n{said[-600:]}")
RAN.append("a confirmed item beside a format error still fails")
code, said, _ = run(CHECK, write(swap("- writing: pass\n", "", out("unknown")), "- Output: unknown | yes\n"))
if code != 1:
    fail("a confirmed item beside a format error still fails", f"exit {code}\n{said[-600:]}")
RAN.append("a stale confirmation is a note")
code, said, _ = run(CHECK, write(GOOD, "- Output: unknown | yes\n"))
if code != 0 or "NOTE" not in said:
    fail("a stale confirmation is a note", f"exit {code}\n{said[-600:]}")
RAN.append("only yes confirms")
code, said, _ = run(CHECK, write(out("ok"), "- Output: ok | no\n"))
if code not in (1, 2):
    fail("only yes confirms", f"exit {code}\n{said[-600:]}")
RAN.append("--confirmed names another file")
other = os.path.join(tempfile.mkdtemp(), "answers.md")
with open(other, "w", encoding="utf-8") as handle:
    handle.write("- Output: ok | yes\n")
for script in (CHECK, MAP):
    code, said, _ = run(script, write(out("ok")), "--confirmed", other)
    if code != 0:
        fail("--confirmed names another file", f"{os.path.basename(script)} exit {code}\n{said[-600:]}")
RAN.append("the mapper copies a confirmed value into the brief's Confirmed block")
code, brief, _ = run(MAP, write(out("ok"), "- Output: ok | yes\n"))
if code != 0 or "## Confirmed\n\n- Output: ok" not in brief:
    fail("the mapper copies a confirmed value into the brief's Confirmed block", f"exit {code}\n{brief}")

# 6. No input crashes. Dotless i in a field name or heading gives a clean result.
for label, text, codes in (
        ("dotless writing field", swap("- writing: pass", "- wrıting: pass"), (1, 3)),
        ("dotless write first", added("- wrıte first: a votes.json file"), (0, 1, 2, 3)),
        ("dotless investigate", added("- ınvestigate: the old app"), (0, 1, 2, 3)),
        ("dotless Decided heading", swap("## Decided", "## Decıded"), (1, 3)),
        ("dotless Open heading", swap("## Open", "## Openı"), (1, 3)),
        ("long s field", swap("- stop: done", "- ſtop: done"), (1, 3))):
    for script in (CHECK, MAP):
        RAN.append(f"no crash: {label}: {os.path.basename(script)}")
        code, said, err = run(script, write(text))
        if code not in codes or "Traceback" in err + said:
            fail(f"no crash: {label}: {os.path.basename(script)}", f"exit {code}\n{err[-400:]}")

# 7. Every Why and Suggest line is plain words that pass the shared writing check.
lines = [line.strip() for said in SAID for line in said.splitlines() if line.strip().startswith(("Why:", "Suggest:"))]
RAN.append("why and suggest lines pass the writing check")
path = os.path.join(tempfile.mkdtemp(), "lines.md")
with open(path, "w", encoding="utf-8") as handle:
    handle.write("\n\n".join(lines) + "\n")
code, said, _ = run(WRITING, path)
if not lines or code != 0:
    fail("why and suggest lines pass the writing check", f"{len(lines)} lines, exit {code}\n{said[-800:]}")
for line in set(lines):
    RAN.append(f"one or two sentences: {line[:40]}")
    if len(re.findall(r"[.?!](?=\s|$)", line)) not in (1, 2):
        fail(f"one or two sentences: {line}", "")

# 8. Saved cases: each case's confirmed.md is a regression. Without it, exit 2 with the expected list. With it, exit 0
# and the mapped brief passes check_brief.
saved = sorted(glob.glob(os.path.join(CASES, "*", "confirmed.md")))
RAN.append("there is a saved check-with-me case")
if not saved:
    fail("there is a saved check-with-me case", f"no */confirmed.md under {CASES}")
for confirmed in saved:
    folder = os.path.dirname(confirmed)
    name = os.path.basename(folder)
    text = open(os.path.join(folder, "decisions.md"), encoding="utf-8").read()
    want = open(os.path.join(folder, "expected.txt"), encoding="utf-8").read()
    RAN.append(f"case {name} without confirmed.md")
    code, said, _ = run(CHECK, write(text))
    section = said[said.find("CHECK WITH ME"):].split("\nCHECK WITH ME decisions:", 1)[0].rstrip() + "\n"
    if code != 2 or section != want:
        fail(f"case {name} without confirmed.md", f"exit {code}\n--- got\n{section}--- want\n{want}")
    RAN.append(f"case {name} with confirmed.md")
    code, said, _ = run(CHECK, os.path.join(folder, "decisions.md"))
    mcode, brief, _ = run(MAP, os.path.join(folder, "decisions.md"))
    if code != 0 or mcode != 0 or brief_passes(brief)[0] != 0:
        fail(f"case {name} with confirmed.md", f"exit {code}, mapper {mcode}\n{said[-600:]}\n{brief[-600:]}")

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
