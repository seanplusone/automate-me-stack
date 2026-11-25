#!/usr/bin/env python3
"""Checks a verify.md written by `verify-web pr`, so review-pr can read it without guessing.

Usage: python3 check_verify.py <evidence dir>/verify.md

Fails when:
- the Base or Head line is missing or has no sha;
- there are fewer than 2 or more than 5 scenarios;
- a scenario lacks Claimed, Steps, Base, Head, Evidence or Verdict;
- a verdict is not VERIFIED, CONTRADICTED or `NOT RUN: <why>`;
- a VERIFIED or CONTRADICTED scenario lists no evidence file, or a listed file is not in the folder;
- a VERIFIED scenario lacks `Persist: reload`, `fresh-context` or `none`, or (for `reload` or `fresh-context`) lacks distinct, listed, existing `Before screenshot:` and `Persist screenshot:` files where the persist screenshot is a real image with different bytes;
- a VERIFIED scenario repeats `Persist:`, `Persist screenshot:`, or `Before screenshot:`;
- the Summary line does not match the verdicts.
Prints PASS or FAIL and exits 1 on FAIL.
"""
import os
import re
import sys

FIELDS = ("Claimed", "Steps", "Base", "Head", "Evidence", "Verdict")
SHA = re.compile(r"\b[0-9a-f]{7,40}\b")
PERSIST_VALUES = ("reload", "fresh-context", "none")
PERSIST_FIELDS = ("Persist", "Persist screenshot", "Before screenshot")


def is_image(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        return False
    with open(path, "rb") as f:
        hdr = f.read(12)
    if ext == ".png":
        return hdr.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return hdr.startswith(b"\xff\xd8\xff")
    return len(hdr) >= 12 and hdr[:4] == b"RIFF" and hdr[8:12] == b"WEBP"


def parse(text):
    head, scenarios, cur = {}, [], None
    for line in text.splitlines():
        m = re.match(r"^## (S\d+)\.\s+(.+)$", line)
        if m:
            cur = {"id": m.group(1), "title": m.group(2), "_counts": {}}
            scenarios.append(cur)
            continue
        m = re.match(r"^(\w[\w ]*?):\s*(.*)$", line)
        if m:
            target = cur if cur is not None else head
            key, val = m.group(1), m.group(2).strip()
            if cur is not None and key in PERSIST_FIELDS:
                cur["_counts"][key] = cur["_counts"].get(key, 0) + 1
            target[key] = val
            if key == "Summary":
                head["Summary"] = val
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
            if v == "VERIFIED":
                dups = [k for k in PERSIST_FIELDS if s["_counts"].get(k, 0) > 1]
                for k in dups:
                    fails.append(f"{sid}: duplicate {k}:")
                if not dups:
                    persist = s.get("Persist", "")
                    if persist not in PERSIST_VALUES:
                        fails.append(f"{sid}: VERIFIED needs Persist: reload, fresh-context or none, got {persist!r}")
                    elif persist in ("reload", "fresh-context"):
                        shot = s.get("Persist screenshot", "")
                        before = s.get("Before screenshot", "")
                        shot_path = None
                        before_path = None
                        if not shot or "/" in shot or "\\" in shot:
                            fails.append(f"{sid}: VERIFIED needs Persist screenshot: <filename in folder>, got {shot!r}")
                        else:
                            p = os.path.join(folder, shot)
                            if not os.path.isfile(p):
                                fails.append(f"{sid}: Persist screenshot not in the folder: {shot}")
                            else:
                                shot_path = p
                        if not before or "/" in before or "\\" in before:
                            fails.append(f"{sid}: VERIFIED needs Before screenshot: <filename in folder>, got {before!r}")
                        else:
                            bp = os.path.join(folder, before)
                            if not os.path.isfile(bp):
                                fails.append(f"{sid}: Before screenshot not in the folder: {before}")
                            else:
                                before_path = bp
                        if shot and shot not in files:
                            fails.append(f"{sid}: Persist screenshot not listed in Evidence: {shot}")
                        if before and before not in files:
                            fails.append(f"{sid}: Before screenshot not listed in Evidence: {before}")
                        if shot and before and shot == before:
                            fails.append(f"{sid}: Persist screenshot must not reuse Before screenshot: {shot}")
                        if shot_path and not is_image(shot_path):
                            fails.append(f"{sid}: Persist screenshot must be a non-empty png, jpg, jpeg or webp image: {shot}")
                        if shot_path and before_path and shot != before:
                            if open(shot_path, "rb").read() == open(before_path, "rb").read():
                                fails.append(f"{sid}: Persist screenshot has the same bytes as Before screenshot: {shot}")
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
