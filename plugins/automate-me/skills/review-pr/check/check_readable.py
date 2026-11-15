"""Lists functions the diff adds or grows past MAX_FN_LINES, so a reviewer can check they stay followable.

Usage: python3 check_readable.py <base> <head>

A function is a block that starts with a common function keyword (def, function, fn, func, fun)
and runs until the next function at the same or a shallower indent, or the end of the file.
Only functions the diff touches are listed. Generated paths (hashed names, .gz, dist/, vendor/)
are skipped.

Prints PASS when nothing is over the cap, or FAIL with path:line, the name, and the line count.
A listed function is a candidate, not an automatic defect. The playbook says when it is a finding.
"""
import os
import re
import subprocess
import sys

MAX_FN_LINES = 80
FN_START = re.compile(
    r"^(\s*)(?:(?:pub(?:lic)?|private|protected|internal|export|async|static)\s+)*"
    r"(?:async\s+)?(?:def|function|fn|func|fun)\s+([A-Za-z_][\w]*)"
)
GENERATED = re.compile(r"(^|/)(dist|vendor|generated)(/|$)|[-.][A-Za-z0-9]{8,}\.(js|css)$|\.gz$")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def changed_files(base, head):
    out = []
    for line in git("diff", "--name-status", f"{base}...{head}").splitlines():
        if not line or line[0] == "D":
            continue
        path = line.split("\t")[-1]
        if GENERATED.search(path):
            continue
        out.append(path)
    return out


def touched_lines(base, head, path):
    lines = set()
    raw = git("diff", "-U0", f"{base}...{head}", "--", path)
    at = 0
    for row in raw.splitlines():
        if row.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", row)
            if m:
                at = int(m.group(1))
                if m.group(2) == "0":
                    at = 0
        elif row.startswith("+") and not row.startswith("+++") and at:
            lines.add(at)
            at += 1
    return lines


def functions(text):
    rows = text.splitlines()
    starts = []
    for i, row in enumerate(rows, 1):
        m = FN_START.match(row)
        if m:
            starts.append((i, len(m.group(1)), m.group(2)))
    out = []
    for n, (start, indent, name) in enumerate(starts):
        end = len(rows)
        for nxt, nxt_indent, _ in starts[n + 1:]:
            if nxt_indent <= indent:
                end = nxt - 1
                break
        out.append((name, start, end))
    return out


def check_readable(base, head):
    hits = []
    for path in changed_files(base, head):
        try:
            text = git("show", f"{head}:{path}")
        except subprocess.CalledProcessError:
            continue
        touched = touched_lines(base, head, path)
        if not touched:
            continue
        for name, start, end in functions(text):
            length = end - start + 1
            if length > MAX_FN_LINES and any(start <= n <= end for n in touched):
                hits.append(f"{path}:{start} {name} {length} lines, max {MAX_FN_LINES}")
    return hits


def main(argv):
    hits = check_readable(argv[1], argv[2])
    print(f"{'FAIL' if hits else 'PASS'} readable: {len(hits)} function{'s' if len(hits) != 1 else ''} over {MAX_FN_LINES} lines")
    for h in hits:
        print(f"  {h}")
    return 1 if hits else 0


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 2)
    sys.exit(main(sys.argv))
