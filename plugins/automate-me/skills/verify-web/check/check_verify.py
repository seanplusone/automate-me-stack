#!/usr/bin/env python3
"""Checks a verify.md written by `verify-web pr`, so review-pr can read it without guessing.

Usage: python3 check_verify.py <evidence dir>/verify.md

Fails when:
- the Base or Head line is missing or has no sha;
- there are fewer than 2 or more than 5 scenarios;
- a scenario lacks Claimed, Steps, Base, Head, Evidence or Verdict;
- a verdict is not VERIFIED, CONTRADICTED or `NOT RUN: <why>`;
- a VERIFIED or CONTRADICTED scenario lists no evidence file, or a listed file is not in the folder;
- the Summary line does not match the verdicts.
Prints PASS or FAIL and exits 1 on FAIL.
"""
import os
import re
import sys

FIELDS = ("Claimed", "Steps", "Base", "Head", "Evidence", "Verdict")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")


def parse(text):
    head, scenarios, cur = {}, [], None
    for line in text.splitlines():
        m = re.match(r"^## (S\d+)\.\s+(.+)$", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2)}
            scenarios.append(cur)
            continue
        m = re.match(r"^(\w[\w ]*?):\s*(.*)$", line)
        if m:
            (cur if cur is not None else head)[m.group(1)] = m.group(2).strip()
            if m.group(1) == "Summary":
                head["Summary"] = m.group(2).strip()
    return head, scenarios


def check(path):
    fails = []
    folder = os.path.dirname(os.path.abspath(path))
    head, scenarios = parse(open(path).read())
    for k in ("Base", "Head"):
        if not SHA.search(head.get(k, "")):
            fails.append(f"header {k}: needs '<branch> <sha>' of the tree that served the page")
    if not 2 <= len(scenarios) <= 5:
        fails.append(f"{len(scenarios)} scenarios; derive 2 to 5 from the PR")
    counts = {"CONTRADICTED": 0, "VERIFIED": 0, "NOT RUN": 0}
    for s in scenarios:
        sid = s["id"]
        for f in FIELDS:
            if not s.get(f):
                fails.append(f"{sid}: missing {f}:")
        v = s.get("Verdict", "")
        if v in ("VERIFIED", "CONTRADICTED"):
            counts[v] += 1
            files = [x.strip() for x in s.get("Evidence", "").split(",") if x.strip()]
            if not files:
                fails.append(f"{sid}: {v} needs at least one evidence file")
            for x in files:
                if not os.path.exists(os.path.join(folder, x)):
                    fails.append(f"{sid}: evidence file not in the folder: {x}")
        elif re.match(r"^NOT RUN: \S", v):
            counts["NOT RUN"] += 1
        elif v:
            fails.append(f"{sid}: verdict must be VERIFIED, CONTRADICTED or 'NOT RUN: <why>', got {v!r}")
    want = f"{counts['CONTRADICTED']} CONTRADICTED, {counts['VERIFIED']} VERIFIED, {counts['NOT RUN']} NOT RUN"
    if head.get("Summary") != want:
        fails.append(f"Summary line must read: Summary: {want}")
    print(f"{'FAIL' if fails else 'PASS'} verify.md: {path}")
    for f in fails:
        print(f"  {f}")
    return fails


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(1 if check(sys.argv[1]) else 0)
