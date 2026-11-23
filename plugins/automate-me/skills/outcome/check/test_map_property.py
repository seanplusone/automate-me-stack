"""Run: python3 check/test_map_property.py

Property over the committed fixtures and cases, plus seeded random mutations of the ones that pass:
- check_decisions and the mapper exit only 0, 1, 2 or 3, the same code, and never raise;
- the mapper prints a brief exactly when the exit is 0, and check_brief passes every brief it prints;
- on exit 2, a confirmed.md that says yes to every CHECK WITH ME item reaches exit 0, and that brief passes too. The one
  item a yes cannot clear is an Evals line with no pass case and fail case, which check_brief asks about itself;
- a confirmation never clears a format error: a file that exits 1 still exits 1 with every item confirmed.
Every label that empties its value (`decide: stated:`) fails, on its own and inside the mutations.
"""
import contextlib
import io
import os
import pathlib
import random
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_brief import ask_lines, check  # noqa: E402
from map_decisions import main as map_main  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "shape-idea", "check")))
from check_decisions import main as decisions_main  # noqa: E402
from test_break import fixture_texts  # noqa: E402

SKILLS = os.path.normpath(os.path.join(HERE, "..", ".."))
SEED = 4
COUNT = 400
SECTIONS = ("## Decided", "## Open", "## Parked")
DECIDED = [
    "output: unknown", "output: unknown for now", "output: Unknown, CSV or JSON", 'output: "unknown": CSV or JSON',
    "output: unknown file types go to an Other folder", "output: stated: unknown - ask Sam", "output: TBD",
    "output: ok", "output: maybe", "output: not sure yet", "output: <channel>", "output: a CSV with `<day>` columns",
    "tools: Unknown for now", "tools: unknown, Slack or Teams", "tools: unknown: Slack or Teams", "tools: Slack only",
    "**tools:** Slack only", "tool: Slack only", "tools:", "tools: write first: none", "agents: unknown for now",
    "agents: me, and a friend checks it", "decide: unknown so far", "decide: which spot to book", "**decide:** maybe",
    "evals: pass: a poll with 3 choices; fail: a poll with none", "evals: pass: unknown for now; fail: unknown, ask Sam",
    "evals: a poll with 3 choices works and a poll with none errors", "evals: pass: TBD", "eval: pass: ok; fail: x",
    "write first: a votes.json file", "out of scope: AI", "**out of scope:** payments", "out of scope: unknown for now",
    "how: ok", "how: fold the paper first", "investigate: the old app", "stated: ok", "stated: TBD", "default to blue",
    "the form submits on <Enter>", "it should look clean", "should a link expire?", "unknown until Friday",
    "Unknown senders get a folder", "the button says 'What's next?'", "goal: Default to a poll in the chat",
    "done: investigate: why a vote is lost", "verify: it looks good", "constraints: none",
    "output: (unknown), CSV or JSON", "output: [unknown](https://example.org/status)", "decide: stated:",
    "tools: stated:", "agents: **stated:**", "evals: stated:", "write first: stated:", "stated:", "out of scope: stated:",
    "stated: `<col>` is the literal header", "`stated: the header row is fixed`", "goal: default new users to dark mode",
    "constraints: unknown senders get nothing", "out of scope: stated: unknown for now", "stated: how: clean",
    "out of scope\uff1acatering", "decide: default to the cheapest spot",
    'output: "the winner only, or the full tally?"', "output: (a list or a page?)", "output: 勝者だけ、それとも全票？",
    "deadline: unknown", "tools: chat API: unknown", "agents: reviewer: unknown", "output: status: unknown",
    "output: https://unknown.example.org/status",
    "go-live date: unknown", "output: file format (CSV/JSON): unknown", "tools: Node.js version: unknown",
    "output: [format](https://example.org/spec): unknown", "output: format:unknown", "output: **CSV or JSON?**",
    'output: a Slack message that asks "Who\'s in for lunch?"', "agents: on-call reviewer: unknown",
    "stated: how: out of scope: maybe", "wr\u0131te first: a votes.json file", "\u0131nvestigate: the old app",
    "output: maybe a CSV", "done: it should look clean", "output: <goal>", "<any other firm choice>",
]
OPEN = [
    "tools: ?", "evals: TBD?", "agents: unknown: ?", "decide: ?", "tools: Should the poll run in <channel>?",
    "tools: Slack or Teams?", "evals: which case should fail?", "Should the button say 'What's next?' or 'Continue'?",
    'should the label say "Continue?"', "should it sync with https://example.org/sync?", "unknown: ?",
    "is it a list (or a page?) or both?", "who votes? and when?", "output: what comes back?", "**tools:** which one?",
    "should the bot use <channel>?", "reminders are not settled", "Should it press <Enter> to confirm each move?",
    "goal: which spot first?", "tools: stated: ?", "投票は20分で締め切る？",
    "**Should the poll close after 20 minutes?**", "TBD?", "<question>?",
]
PARKED = [
    "out of scope: AI", "**out of scope:** AI", "out of scope: a watch app", "out of scope: unknown for now",
    "dark mode, maybe not now", "I think we should skip dietary tags, not now", "a native app, later",
    "ship it later?", "the form submits on <Enter>", "later, perhaps", "TBD", "unknown", "unknown senders get a folder",
    "investigate: the old app", "how: ok", "clean", "ask about <channel> later", "a share button for later",
    "stated:", "out of scope: stated:", "out of scope\uff1acatering", "stated: run `make check` first",
    "out of scope: a watch app, or later?", "out of scope: **Should dietary tags be excluded?**",
    "**Should the poll close after 20 minutes?**", "stated: how: unknown", "unknown: later",
]
EMPTY = ["decide: stated:", "tools: stated:", "agents: stated:", "evals: stated:", "write first: stated:", "stated:",
         "**stated:**", "out of scope: stated:", "goal: stated:", "output: **stated:**", "decide: `stated:`"]


def sources():
    files = sorted(pathlib.Path(SKILLS, "outcome", "cases", "from-decisions").glob("*/decisions.md"))
    files += sorted(pathlib.Path(SKILLS, "shape-idea", "cases").glob("*/runs/run-1/decisions.md"))
    return [text for _, text in fixture_texts()] + [path.read_text(encoding="utf-8") for path in files]


def mutate(text, rng):
    lines = text.splitlines()
    for _ in range(rng.randint(1, 3)):
        heads = [i for i, line in enumerate(lines) if line.strip() in SECTIONS]
        if not heads:
            break
        head = rng.choice(heads)
        pool = {"## Decided": DECIDED, "## Open": OPEN, "## Parked": PARKED}[lines[head].strip()]
        end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("#")), len(lines))
        bullets = [i for i in range(head + 1, end) if lines[i].startswith("- ")]
        new = "- " + rng.choice(pool)
        if bullets and rng.random() < 0.5:
            lines[rng.choice(bullets)] = new
        else:
            lines.insert(head + 2 if head + 2 <= end else head + 1, new)
    if rng.random() < 0.05:
        lines = [rng.choice(["## Dec\u0131ded", "- wr\u0131ting: pass", "- \u017ftop: done"]) if line in
                 ("## Decided", "- writing: pass", "- stop: done") and rng.random() < 0.5 else line for line in lines]
    return "\n".join(lines) + "\n"


def write(text, confirmed=None):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if confirmed is not None:
        with open(os.path.join(folder, "confirmed.md"), "w", encoding="utf-8") as handle:
            handle.write(confirmed)
    return path


def run(entry, path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = entry(path)
    return code, buf.getvalue()


def brief_exit(brief):
    if any(fails for _, fails in check(brief)):
        return 1
    return 2 if ask_lines(brief) else 0


def listed(said):
    """(slot, value) for each CHECK WITH ME item."""
    if "CHECK WITH ME (" not in said:
        return []
    return re.findall(r'^- ([^:\n]+): "(.*)"$', said.split("CHECK WITH ME (", 1)[1], re.M)


def violations(text, confirmed=None):
    path = write(text, confirmed)
    dec, said = run(decisions_main, path)
    code, printed = run(map_main, path)
    bad = []
    if dec not in (0, 1, 2, 3) or code != dec:
        bad.append(f"check_decisions exit {dec}, mapper exit {code}")
    if (code == 0) != printed.startswith("# Brief"):
        bad.append(f"mapper exit {code}, printed a brief: {printed.startswith('# Brief')}")
    if code == 0 and brief_exit(printed) != 0:
        bad.append(f"check_brief exits {brief_exit(printed)} on the printed brief")
    if code == 2 and not listed(said):
        bad.append("exit 2 with no CHECK WITH ME item")
    return bad, dec, said


start = time.time()
rng = random.Random(SEED)
bases = sources()
ready = [text for text in bases if violations(text)[1] == 0]
texts = bases + [mutate(rng.choice(ready), rng) for _ in range(COUNT)]
FAILS = []
spread = {0: 0, 1: 0, 2: 0, 3: 0}
cleared = 0
for number, text in enumerate(texts):
    try:
        bad, dec, said = violations(text)
        spread[dec] += 1
        items = listed(said)
        if dec in (1, 2) and items:
            yes = "".join(f"- {slot}: {value} | yes\n" for slot, value in items)
            again, after, said_after = violations(text, yes)
            bad += [f"with every item confirmed: {item}" for item in again]
            evals_only = all(slot == "Evals" for slot, _ in listed(said_after))
            if dec == 1 and after != 1:
                bad.append(f"a confirmation cleared a format error: exit {after}")
            if dec == 2 and after != 0 and not (after == 2 and evals_only):
                bad.append(f"confirming every item gave exit {after}\n{said_after[-600:]}")
            cleared += dec == 2 and after == 0
    except Exception as exc:
        bad = [f"crashed: {exc!r}"]
    if bad:
        FAILS.append(f"{number}: {bad}\n{text}")
if min(spread[0], spread[1], spread[2]) < COUNT // 20:
    FAILS.append(f"mutations do not reach every exit: {spread}")
if cleared < COUNT // 20:
    FAILS.append(f"too few files reach exit 0 once confirmed: {cleared}")
for line in EMPTY:
    for head in ("## Open", "## Handoff"):
        text = ready[0].replace(head, f"- {line}\n\n{head}", 1)
        try:
            got = violations(text)[1]
        except Exception as exc:
            got = f"crashed: {exc!r}"
        if got != 1:
            FAILS.append(f"an empty label does not fail before {head}: {line!r}: {got}")
elapsed = time.time() - start

if __name__ == "__main__":
    for item in FAILS[:15]:
        print(f"FAIL {item}")
    print(f"{len(texts) - len(FAILS)}/{len(texts)} files hold the property, seed {SEED}, exits {spread}, "
          f"{cleared} cleared by confirmed.md, {elapsed:.1f}s")
    if elapsed > 60:
        print(f"FAIL property test took {elapsed:.1f}s, over 60s")
    sys.exit(1 if FAILS or elapsed > 60 else 0)
