"""Checks a RESUME.md against shared/resume-shape.md. Self-report is never proof: every done item needs a pointer that resolves.

Usage: python3 check_resume.py <resume.md> [--root DIR] [--git-dir DIR]

The format:

    # Resume: <short title>

    - Goal: <the run's goal>
    - Branch: <branch name, or none>
    - Status: in progress | waiting on user | blocked | done
    - Done and verified:
      - <item> | evidence: <pointer>
    - Not done: <what's left>
    - Next step: <the first action on pickup>
    - Key files: <paths>
    - Gotchas: <or none>
    - Waiting on: <the question, or none>
    - Repro test: <path to a NEW test, or none: not a bug fix>
    - Repro at parent: <fail evidence, or none>
    - Repro at head: <pass evidence, or none>

Each slot appears once. Goal, Next step and Key files are never empty or none. Status is one of the four values.
Done and verified is `none` only when nothing is done (and Status is not done); otherwise one list line per item.

Pointer kinds. Paths are relative to --root, default the folder that holds the resume:
1. a log path that exists: `logs/x.txt` or `log: logs/x.txt`;
2. a script that exists, its exit code and a log that exists: `script: checks/lint.sh exit 0 log: logs/lint.txt`;
3. a commit SHA, full or unambiguous short, in --git-dir (default: the current repo).
A pointer of only words fails as self-report. A dangling or empty log, or an unknown SHA, fails even next to one that resolves.
A hex-shaped branch or tag name is not a SHA. Quoted paths with spaces are allowed: `log: "logs/trim parent.txt"`.

Repro: all three slots none for a run that fixes no bug. Otherwise Repro test is a path that exists, Repro at parent is fail
evidence (a non-empty log and a recorded exit that is not 0) and Repro at head is pass evidence (exit 0 and a non-empty log).

Prints PASS or FAIL and exits 1 on FAIL.
"""
import argparse
import os
import re
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_writing import FAILED, report  # noqa: E402

SLOTS = ["Goal", "Branch", "Status", "Done and verified", "Not done", "Next step", "Key files", "Gotchas",
         "Waiting on", "Repro test", "Repro at parent", "Repro at head"]
REQUIRED = {"Goal", "Next step", "Key files", "Status"}
STATUS = ["in progress", "waiting on user", "blocked", "done"]
REPRO = ["Repro test", "Repro at parent", "Repro at head"]

TITLE = re.compile(r"^# Resume:\s*(.*)$")
SLOT = re.compile(r"^- ([A-Za-z ]+?):(.*)$")
ITEM = re.compile(r"^\s*- (.*)$")
EXIT = re.compile(r"\bexit(?:\s+code)?\s*[:=]?\s*(-?\d+)\b")
SHA = re.compile(r"(?:commit:|sha:)?([0-9a-f]{7,40})", re.I)
PATHLIKE = re.compile(r"/|[^./]\.[A-Za-z]\w{0,4}$")
REPORT = re.compile(r"^(tests passed|i checked|ok|done|step \d+ done|passed)\.?$", re.I)
LABELED = re.compile(r'\b(script|log):\s*("([^"]+)"|\'([^\']+)\'|(\S+))')


def is_none(value):
    return re.fullmatch(r"none(:.*)?", value.strip(), re.I) is not None


def clean(tok):
    return tok.strip("`'\"()[]<>").rstrip(".,;:")


def labeled_paths(text):
    """Pulls `script:` and `log:` values, including quoted paths with spaces, and returns (scripts, logs, rest)."""
    scripts, logs = [], []
    for m in LABELED.finditer(text):
        value = next(g for g in m.groups()[2:] if g is not None)
        (scripts if m.group(1) == "script" else logs).append(value)
    return scripts, logs, LABELED.sub(" ", text)


def parse_pointer(text):
    """Splits an evidence pointer into scripts, logs, exit codes and SHAs. Plain words are dropped."""
    scripts, logs, rest = labeled_paths(text)
    p = {"scripts": scripts, "logs": logs, "exits": [int(n) for n in EXIT.findall(rest)], "shas": []}
    rest = EXIT.sub(" ", rest)
    try:
        tokens = shlex.split(rest)
    except ValueError:
        tokens = rest.split()
    for raw in tokens:
        tok = clean(raw)
        m = SHA.fullmatch(tok)
        if m:
            p["shas"].append(m.group(1).lower())
        elif tok and "://" not in tok and PATHLIKE.search(tok):
            p["logs"].append(tok)
    return p


def sha_exists(sha, git_dir):
    """True when sha is an object-id prefix in git_dir, not a branch or tag whose name happens to be hex."""
    r = subprocess.run(["git", "-C", git_dir, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False
    ref = subprocess.run(["git", "-C", git_dir, "rev-parse", "--verify", "--quiet", "--symbolic-full-name", sha],
                         capture_output=True, text=True)
    if ref.stdout.strip():
        return False
    return r.stdout.strip().lower().startswith(sha.lower())


def resolve(text, root, git_dir, where):
    """Returns (fails, pointer). A pointer passes when one part resolves and no part dangles."""
    p = parse_pointer(text)
    fails = []
    ok = False
    for s in p["scripts"]:
        if not os.path.isfile(os.path.join(root, s)):
            fails.append(f"{where}: script does not exist: {s}")
    if p["scripts"] and not p["exits"]:
        fails.append(f"{where}: script has no recorded exit code. Write `exit N`")
    if p["scripts"] and not p["logs"]:
        fails.append(f"{where}: script has no log. Write `log: <path>`")
    for log in p["logs"]:
        path = os.path.join(root, log)
        if not os.path.isfile(path):
            fails.append(f"{where}: path does not exist: {log}")
        elif os.path.getsize(path) == 0:
            fails.append(f"{where}: log is empty: {log}")
        elif REPORT.fullmatch(open(path).read().strip()):
            fails.append(f"{where}: log is self-report: {log}")
        else:
            ok = True
    for sha in p["shas"]:
        if sha_exists(sha, git_dir):
            ok = True
        else:
            fails.append(f"{where}: unknown commit: {sha}")
    if not ok and not fails:
        fails.append(f"{where}: self-report only, no pointer resolves: {text.strip() or '(empty)'}")
    return fails, p


def parse(lines):
    """Returns (title, slots, items, fails). slots maps a label to its values, one per time it appears."""
    title, slots, items, fails = None, {}, [], []
    current = None
    seen = False
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        t = TITLE.match(line)
        if t and title is None:
            if seen:
                fails.append("first heading must be `# Resume: <short title>` on the first non-empty line")
            title = t.group(1).strip()
            seen = True
            continue
        if title is None:
            seen = True
            fails.append("first heading must be `# Resume: <short title>` on the first non-empty line")
            # keep scanning so later slots are still checked
        s = SLOT.match(line)
        if s and s.group(1) in SLOTS:
            current = s.group(1)
            slots.setdefault(current, []).append(s.group(2).strip())
            continue
        if current != "Done and verified":
            continue
        # Every list line up to the next slot is a done item, indented or not, so none slips past the check.
        i = ITEM.match(line)
        if i:
            items.append((n, i.group(1).strip()))
        else:
            fails.append(f"line {n}: unexpected line in Done and verified: {line.strip()}")
    return title, slots, items, fails


def check_done(slots, items, root, git_dir):
    fails = []
    value = slots["Done and verified"][0]
    if is_none(value):
        if items:
            fails.append("Done and verified is none but lists items")
        if slots.get("Status", [""])[0] == "done":
            fails.append("Done and verified is none but Status is done")
        return fails
    if value:
        fails.append(f"Done and verified: put each item on its own list line, not after the label: {value}")
    if not items:
        fails.append("Done and verified is empty. List items, or write none when nothing is done yet")
    for n, text in items:
        if "evidence:" not in text:
            fails.append(f"line {n}: self-report only, no `| evidence: <pointer>`: {text}")
            continue
        claim, pointer = text.rsplit("evidence:", 1)
        if not claim.strip(" |"):
            fails.append(f"line {n}: done item has no description")
        fails += resolve(pointer, root, git_dir, f"line {n}")[0]
    return fails


def check_repro(slots, root, git_dir):
    test, parent, head = (slots[k][0] for k in REPRO)
    if is_none(test):
        return [f"{k} must be none when Repro test is none" for k, v in zip(REPRO[1:], (parent, head)) if not is_none(v)]
    fails = []
    paths = parse_pointer(test)["logs"]
    if not paths:
        fails.append(f"Repro test: not a path: {test}")
    for p in paths:
        if not os.path.isfile(os.path.join(root, p)):
            fails.append(f"Repro test: path does not exist: {p}")
    for label, value, want_pass in (("Repro at parent", parent, False), ("Repro at head", head, True)):
        if is_none(value):
            fails.append(f"{label} is none but Repro test names a test")
            continue
        errs, p = resolve(value, root, git_dir, label)
        fails += errs
        if not p["logs"]:
            fails.append(f"{label}: needs a log path that exists")
        if want_pass and p["exits"] != [0]:
            fails.append(f"{label}: needs `exit 0` as pass evidence, got {p['exits'] or 'no exit'}")
        if not want_pass and (not p["exits"] or 0 in p["exits"]):
            fails.append(f"{label}: needs a non-zero exit, because the new test must fail at the parent")
    return fails


def check_resume(path, root=None, git_dir=None):
    root = root or os.path.dirname(os.path.abspath(path))
    git_dir = git_dir or os.getcwd()
    with open(path) as f:
        title, slots, items, fails = parse(f)
    if title is None:
        fails.append("first heading must be `# Resume: <short title>`")
    elif not title:
        fails.append("title is empty")
    for label in SLOTS:
        got = slots.get(label, [])
        if not got:
            fails.append(f"missing slot: {label}")
        elif len(got) > 1:
            fails.append(f"slot appears {len(got)} times: {label}")
    present = {k: v for k, v in slots.items() if len(v) == 1}
    for label in SLOTS:
        if label not in present or label == "Done and verified":
            continue
        value = present[label][0]
        if not value:
            fails.append(f"empty slot: {label}")
        elif label in REQUIRED and is_none(value):
            fails.append(f"{label} cannot be none")
    status = present.get("Status", [""])[0]
    if status and status not in STATUS:
        fails.append(f"Status must be one of {', '.join(STATUS)}; got: {status}")
    if status == "waiting on user" and is_none(present.get("Waiting on", ["none"])[0]):
        fails.append("Status is waiting on user, so Waiting on names the question")
    if "Done and verified" in present:
        fails += check_done(present, items, root, git_dir)
    if all(k in present and present[k][0] for k in REPRO):
        fails += check_repro(present, root, git_dir)
    report(f"resume: {path}", fails)
    return fails


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check a RESUME.md against shared/resume-shape.md.")
    ap.add_argument("resume")
    ap.add_argument("--root", help="folder that evidence paths are relative to (default: the resume's folder)")
    ap.add_argument("--git-dir", help="repo that evidence SHAs must exist in (default: the current repo)")
    a = ap.parse_args()
    check_resume(a.resume, a.root, a.git_dir)
    sys.exit(1 if FAILED else 0)
