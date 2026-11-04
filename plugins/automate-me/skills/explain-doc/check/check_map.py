"""Checks an explain-doc map file: its shape, its limits and the writing rules.

Usage: python3 check_map.py <map.json>
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WRITING = os.path.join(HERE, "..", "..", "shared", "check_writing.py")
LABELS = {"measured", "inferred", "guess"}
MAX_SECTIONS = 15
MAX_WRONG = 10
MAX_WORDS = 2500
LINES = re.compile(r"^\d+(-\d+)?(, ?\d+(-\d+)?)*$")


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'])", text.strip()) if s]


def check(m):
    errs, prose = [], []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    def table(t, where):
        need(isinstance(t.get("head"), list) and t["head"], f"{where}: table needs a head")
        for i, r in enumerate(t.get("rows", [])):
            need(len(r) == len(t.get("head", [])), f"{where}: row {i + 1} has {len(r)} cells, head has {len(t.get('head', []))}")
            prose.extend(r)

    need(m.get("title"), "title is missing")
    need(m.get("source", {}).get("path") or m.get("source", {}).get("link"), "source needs a path or a link")
    bp = m.get("big_picture", "")
    need(1 <= len(sentences(bp)) <= 5, f"big_picture has {len(sentences(bp))} sentences, limit 5")
    prose += [bp, m.get("example", ""), m.get("status", "")]

    flow = m.get("flow")
    need(flow, "flow is missing")
    if flow:
        st = flow.get("stages", [])
        need(1 <= len(st) <= 5, f"flow has {len(st)} stages, limit 5")
        prose += [flow.get("title", ""), flow.get("intro", "")]
        for i, s in enumerate(st):
            need(s.get("name") and s.get("text"), f"stage {i + 1} needs a name and text")
            k = len(sentences(s.get("text", "")))
            need(1 <= k <= 3, f"stage {i + 1}: text has {k} sentences, limit 3")
            prose += [s.get("name", ""), s.get("text", ""), s.get("note", "")]
            if s.get("table"):
                table(s["table"], f"stage {i + 1}")

    states = m.get("states") or []
    for sm in states if isinstance(states, list) else [states]:
        need(len(sm.get("names", [])) >= 2, "states needs at least two names")
        for r in sm.get("rows", []):
            need(len(r) == 2, "states rows are [change, who or what does it]")
            prose.extend(r)
        prose += [sm.get("title", ""), sm.get("note", "")]

    for i, d in enumerate(m.get("decisions", [])):
        need(d.get("question") and LINES.match(str(d.get("lines", ""))), f"decision {i + 1} needs a question and lines")
        prose += [d.get("question", ""), d.get("why", "")]

    secs = m.get("sections", [])
    need(1 <= len(secs) <= MAX_SECTIONS, f"{len(secs)} sections, limit {MAX_SECTIONS}; group subsections under their parent")
    need(len(m.get("wrong", [])) <= MAX_WRONG, f"{len(m.get('wrong', []))} looked-wrong items, limit {MAX_WRONG}; keep the ones that change a decision")
    for s in secs:
        n = s.get("name", "?")
        need(LINES.match(str(s.get("lines", ""))) or s.get("files"), f"section {n}: needs lines like 25-36, or files for a code PR")
        k = len(sentences(s.get("summary", "")))
        need(1 <= k <= 2, f"section {n}: summary has {k} sentences, limit 2")
        need(len(s.get("points", [])) <= 4, f"section {n}: {len(s.get('points', []))} points, limit 4")
        prose += [n, s.get("summary", "")] + s.get("points", [])

    for t in m.get("tables", []):
        need(t.get("title"), "a table needs a title")
        table(t, f"table {t.get('title', '?')}")
        prose.append(t.get("intro", ""))

    for i, w in enumerate(m.get("wrong", [])):
        need(LINES.match(str(w.get("lines", ""))) or w.get("files"), f"wrong {i + 1}: lines must look like 33 or 33, 942")
        need(w.get("label") in LABELS, f"wrong {i + 1}: label must be measured, inferred or guess")
        k = len(sentences(w.get("text", "")))
        need(1 <= k <= 3, f"wrong {i + 1}: {k} sentences, limit 3")
        prose.append(w.get("text", ""))

    words = len(" ".join(p for p in prose if p).split())
    need(words <= MAX_WORDS, f"page prose is {words} words, limit {MAX_WORDS}; cut points before sections")
    legend = m.get("legend") if isinstance(m.get("legend"), dict) else {}
    need(legend, "legend is empty")
    body = "\n".join(p for p in prose if p).lower()
    for term, definition in legend.items():
        need(re.search(r"(?<![\w-])" + re.escape(term.lower()) + r"(?:s|es|d|ed|ing)?(?![\w-])", body), f"legend term '{term}' is never used on the page")
        prose.append(definition)
    return errs, [p for p in prose if p]


def main(path):
    m = json.load(open(path, encoding="utf-8"))
    errs, prose = check(m)
    text = "\n\n".join(prose)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
    out = subprocess.run([sys.executable, WRITING, f.name], capture_output=True, text=True)
    os.unlink(f.name)
    for e in errs:
        print("FAIL map:", e)
    if out.returncode:
        rows = text.split("\n")
        for ln in out.stdout.strip().splitlines():
            hit = re.search(r"line (\d+)", ln)
            print(ln + (f"\n    > {rows[int(hit.group(1)) - 1]}" if hit and int(hit.group(1)) <= len(rows) else ""))
    if errs or out.returncode:
        return 1
    shown = prose[:-len(m["legend"])] if m.get("legend") else prose
    print(f"PASS map: {len(m['sections'])} sections, {len(m['flow']['stages'])} stages, {len(' '.join(shown).split())} words of prose, writing clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
