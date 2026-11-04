"""Scores a run's gaps against a case key. The only script that reads key.md.

Usage: python3 check/score_case.py <cases/<name>/key.md> <gaps.txt>
-h prints this and exits 0. A missing argument prints it and exits 2. Exits 1 if any key gap is missed.

A key row is `| <id> | <points> | <question> | <owner> | <PRD evidence> |`, with points such as
`R1, R2` or `PM unsure`. A GAP line in gaps.txt is on target when it names one of those points
(`PM unsure` matches any U point) or quotes the row's evidence.
An optional line `Terms: G01 | right away/real time` below the table also needs one on-target gap's
question to contain every term, case-insensitive. A term written `a/b` matches either.
Without Terms this checks placement only, so any gap on a busy point passes. A person still checks
that each found gap asks the key's question.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check import norm  # noqa: E402

ROW = re.compile(r"^\| (G\d+) \| ([^|]+?) \| [^|]+ \| ([^|]+?) \| ([^|]+?) \|$")


def key_rows(path):
    return [ROW.match(line.strip()).groups() for line in open(path) if ROW.match(line.strip())]


def key_terms(path):
    terms = {}
    for line in open(path):
        m = re.match(r"^Terms:\s*(G\d+)\s*\|(.+)$", line.strip())
        if m:
            terms[m.group(1)] = [t.strip().lower() for t in m.group(2).split("|") if t.strip()]
    return terms


def run_gaps(path):
    """(points, question, owner, quote) for every GAP line."""
    out = []
    for line in open(path):
        m = re.match(r"^GAP \d+:(.*)$", line.strip())
        parts = [p.strip() for p in m.group(1).split("|")] if m else []
        if len(parts) == 4:
            out.append(([p.strip() for p in parts[0].split(",")], parts[1], parts[2], parts[3]))
    return out


def on_target(gap, points, evidence):
    gap_points, _, _, quote = gap
    for p in points:
        if p in gap_points or (p == "PM unsure" and any(g.startswith("U") for g in gap_points)):
            return True
    q = norm(quote).lower()
    quotes = [norm(e).lower() for e in re.findall(r'"([^"]+)"', evidence)]
    return q != "not stated" and any(q in e or e in q for e in quotes)


def missing_terms(gap, terms):
    text = gap[1].lower()
    return [t for t in terms if not any(alt in text for alt in t.split("/"))]


def score(key_path, gaps_path):
    rows, terms, gaps = key_rows(key_path), key_terms(key_path), run_gaps(gaps_path)
    if not rows:
        print(f"FAIL no scorable rows in {key_path}")
        return 1
    missed = 0
    for gid, points_col, owner, evidence in rows:
        points = [p.strip() for p in points_col.split(",")]
        hits = [g for g in gaps if on_target(g, points, evidence)]
        named = [g for g in hits if not missing_terms(g, terms.get(gid, []))]
        if not hits:
            result = f"MISSED no gap on {points_col}"
        elif not named:
            result = f"MISSED no gap on {points_col} names: " + ", ".join(min((missing_terms(g, terms[gid]) for g in hits), key=len))
        else:
            result = "found" + ("" if named[0][2] == owner else f" (owner {named[0][2]}, key {owner})")
        missed += not result.startswith("found")
        print(f"{gid} {result}")
    print(f"{'FAIL' if missed else 'PASS'} {len(rows) - missed}/{len(rows)} key gaps")
    return 1 if missed else 0


if __name__ == "__main__":
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(__doc__.strip())
        sys.exit(0)
    if len(sys.argv) != 3:
        print(__doc__.strip(), file=sys.stderr)
        sys.exit(2)
    sys.exit(score(sys.argv[1], sys.argv[2]))
