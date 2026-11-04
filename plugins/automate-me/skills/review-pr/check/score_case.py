"""Scores a drafts file against a case key's findings table.

Usage: python3 score_case.py <cases/<name>/key.md> <drafts.md>
Exits 1 if any key finding is missed.

A key row is `| <id> | <pr> | <path prefix> | <line or -> | <finding> | <min sites or -> | <proof> |`.
A finding is found when the drafts carry a comment in that PR on a path that starts with the
prefix and, when the row names a line, within LINE_WINDOW lines of it. A row whose path is `PR`
wants a PR-level comment, one with `PR` in place of `<path>:<line>`. The window allows for a
comment anchored on the nearest changed line. A row with a minimum also needs that comment's
`Sites:` count to reach it.
An optional line `Terms: K1 | admin | owner` outside the table also requires one on-target comment
to contain every listed term (case-insensitive, posted comment text only). A term written `a/b`
matches either word.
Without it this checks placement and counts only; wording is still scored by a person.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_drafts import parse  # noqa: E402

ROW = re.compile(r"^\| (K\d+) \| (\S+#\d+) \| `?([^|`]+?)`? \| (\d+|-) \| [^|]+ \| (\d+|-) \| [^|]* \|$")
LINE_WINDOW = 3


def on_target(anchor, prefix, line):
    if anchor == "PR" or prefix == "PR":
        return anchor == prefix
    path, at = anchor.rsplit(":", 1)
    return path.startswith(prefix) and (line == "-" or abs(int(at) - int(line)) <= LINE_WINDOW)


def key_rows(path):
    return [ROW.match(line.strip()).groups() for line in open(path) if ROW.match(line.strip())]


def key_terms(path):
    terms = {}
    for line in open(path):
        m = re.match(r"^Terms:\s*(K\d+)\s*\|(.+)$", line.strip())
        if m:
            terms[m.group(1)] = [t.strip().lower() for t in m.group(2).split("|") if t.strip()]
    return terms


def missing_terms(hits, terms):
    """Terms absent from the on-target comment that lacks the fewest."""
    def absent(term, text):
        return not any(alt in text for alt in term.split("/"))
    return min(([t for t in terms if absent(t, " ".join(f["comment"]).lower())] for f in hits), key=len)


def score(key_path, drafts_path):
    prs, _ = parse(drafts_path)
    rows = key_rows(key_path)
    terms = key_terms(key_path)
    if not rows:
        print(f"FAIL no scorable rows in {key_path}")
        return 1
    missed = 0
    for kid, pr, prefix, line, min_sites in rows:
        hits = [f for p in prs if p["pr"].endswith("/" + pr) or p["pr"] == pr
                for f in p["findings"] if f["match"] and on_target(f["match"].group(2), prefix, line)]
        best = max((int(s.split("|")[0]) for f in hits for s in f["sites"]), default=0)
        if not hits:
            result = "MISSED no comment on " + prefix + ("" if line == "-" else f" near line {line}")
        elif terms.get(kid) and missing_terms(hits, terms[kid]):
            result = "MISSED comment on the line does not name: " + ", ".join(missing_terms(hits, terms[kid]))
        elif min_sites != "-" and best < int(min_sites):
            result = f"MISSED Sites {best or 'absent'}, key needs at least {min_sites}"
        else:
            result = "found"
        missed += result != "found"
        print(f"{kid} {pr} {result}")
    print(f"{'FAIL' if missed else 'PASS'} {len(rows) - missed}/{len(rows)} key findings")
    return 1 if missed else 0


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 2)
    sys.exit(score(sys.argv[1], sys.argv[2]))
