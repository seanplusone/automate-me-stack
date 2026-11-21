"""Run: python3 check/test_map_property.py

Property: the mapper and check_brief agree on every decisions file. The files are the committed fixtures and cases,
plus seeded random mutations of the ones that pass, so most mutations reach the brief check. For each file, `brief` is map_text's brief and `cb` is check_brief's exit on it.
- the mapper exits as check_decisions does;
- mapper exit 0 means it printed that brief, and cb is 0;
- cb 1 means mapper exit 1, and cb 2 means the mapper does not exit 0;
- mapper exit 2 means cb is not 1, and the mapper printed ASK lines and no brief.
A mapper ask with cb 0 comes from a rule check_brief cannot see: a value that starts with "unknown", or a value the
mapper prefixed with `stated:`.
"""
import contextlib
import io
import os
import pathlib
import random
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_brief import ask_lines, check  # noqa: E402
from map_decisions import main as map_main, map_text  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "shape-idea", "check")))
from check_decisions import main as decisions_main  # noqa: E402

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
]
OPEN = [
    "tools: ?", "evals: TBD?", "agents: unknown: ?", "decide: ?", "tools: Should the poll run in <channel>?",
    "tools: Slack or Teams?", "evals: which case should fail?", "Should the button say 'What's next?' or 'Continue'?",
    'should the label say "Continue?"', "should it sync with https://example.org/sync?", "unknown: ?",
    "is it a list (or a page?) or both?", "who votes? and when?", "output: what comes back?", "**tools:** which one?",
    "should the bot use <channel>?", "reminders are not settled",
]
PARKED = [
    "out of scope: AI", "**out of scope:** AI", "out of scope: a watch app", "out of scope: unknown for now",
    "dark mode, maybe not now", "I think we should skip dietary tags, not now", "a native app, later",
    "ship it later?", "the form submits on <Enter>", "later, perhaps", "TBD", "unknown", "unknown senders get a folder",
    "investigate: the old app", "how: ok", "clean", "ask about <channel> later", "a share button for later",
]


def sources():
    files = sorted(pathlib.Path(SKILLS, "shape-idea", "check", "fixtures").glob("*.md"))
    files += sorted(pathlib.Path(SKILLS, "outcome", "cases", "from-decisions").glob("*/decisions.md"))
    files += sorted(pathlib.Path(SKILLS, "shape-idea", "cases").glob("*/runs/run-1/decisions.md"))
    return [path.read_text(encoding="utf-8") for path in files]


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
    if rng.random() < 0.2:
        lines += ["", "## Confirmed", "", "- " + rng.choice(["Output: ok", "Constraints: out of scope: AI",
                                                              "Output: unknown file types go to an Other folder",
                                                              "Done: the form submits on <Enter>", "Goal: maybe"])]
    return "\n".join(lines) + "\n"


def run(entry, path):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = entry(path)
    return code, buf.getvalue()


def brief_exit(brief):
    if any(fails for _, fails in check(brief)):
        return 1
    return 2 if ask_lines(brief) else 0


def violations(text):
    path = os.path.join(tempfile.mkdtemp(), "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    dec, _ = run(decisions_main, path)
    code, said = run(map_main, path)
    brief = map_text(text)
    cb = brief_exit(brief)
    bad = []
    if code != dec:
        bad.append(f"mapper exit {code}, check_decisions exit {dec}")
    if code == 0 and (said != brief or cb != 0):
        bad.append(f"mapper printed a brief check_brief exits {cb} on")
    if cb == 1 and code != 1:
        bad.append(f"check_brief fails the brief, mapper exit {code}")
    if cb == 2 and code == 0:
        bad.append("check_brief asks, mapper exit 0")
    if code == 2 and (cb == 1 or "# Brief" in said or "ASK: " not in said):
        bad.append(f"mapper asked, check_brief exit {cb}")
    return bad


def exit_of(text):
    path = os.path.join(tempfile.mkdtemp(), "decisions.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return run(map_main, path)[0]


start = time.time()
rng = random.Random(SEED)
bases = sources()
ready = [text for text in bases if exit_of(text) == 0]
texts = bases + [mutate(rng.choice(ready), rng) for _ in range(COUNT)]
FAILS = []
spread = {0: 0, 1: 0, 2: 0}
for number, text in enumerate(texts):
    try:
        bad = violations(text)
        spread[exit_of(text)] += 1
    except Exception as exc:
        bad = [f"crashed: {exc!r}"]
    if bad:
        FAILS.append(f"{number}: {bad}\n{text}")
if min(spread.values()) < COUNT // 20:
    FAILS.append(f"mutations do not reach every exit: {spread}")
elapsed = time.time() - start

if __name__ == "__main__":
    for item in FAILS[:15]:
        print(f"FAIL {item}")
    print(f"{len(texts) - len(FAILS)}/{len(texts)} files agree, seed {SEED}, exits {spread}, {elapsed:.1f}s")
    if elapsed > 30:
        print(f"FAIL property test took {elapsed:.1f}s, over 30s")
    sys.exit(1 if FAILS or elapsed > 30 else 0)
