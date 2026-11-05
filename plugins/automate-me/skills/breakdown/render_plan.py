"""Renders a breakdown plan file.

Usage: python3 render_plan.py <plan.json> > page.html          (the artifact page)
       python3 render_plan.py --text <plan.json> > page.txt    (plain text, for the cold read)
       python3 render_plan.py --prompt B <plan.json>           (item B as an agent prompt)
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "explain-doc", "check"))
from render_page import CSS, FONTS, Rich  # noqa: E402

EXTRA = """
.outcome{max-width:70ch;margin-top:14px;background:var(--accent-soft);border-radius:6px;padding:12px 14px;display:grid;gap:4px}
.outcome b{font-family:var(--display)}
.dia{margin-top:14px;overflow-x:auto}
.dia svg{display:block;max-width:100%;height:auto}
.dia rect{fill:var(--panel);stroke:var(--accent);stroke-width:1.5}
.dia text{fill:var(--fg);font:13px var(--body)}
.dia .id{font:600 14px var(--display);fill:var(--accent)}
.dia .e{stroke:var(--muted);stroke-width:1.5;fill:none}
details{border-top:1px solid var(--line);padding:10px 0}
summary{cursor:pointer;font-weight:600}
details>div{margin-top:10px;display:grid;gap:8px}
.ask{max-width:70ch;margin-top:28px;color:var(--muted)}
"""
KEY = ("How to read this. S is one short agent run and M is a longer one. The harness is the check that proves an item is done. "
       "Measured means someone ran or read it, inferred means reasoned from what was read, and guess means neither. "
       "An item marked first goes first because its result can change the items after it.")
NOT_PROOF = ("A passing check is not proof. Show the check failing before the change, then compare the output with the goal "
             "and try one case the check does not cover.")
REVIEW = "Review: before the item closes, an agent that did not write the diff reviews it with review-pr, and every finding is fixed or answered."
EVIDENCE = 'Every claim names the run or file:line behind it, or says "guess".'


def depths(items):
    d = {}
    for it in items:
        d[it["id"]] = 1 + max((d[a] for a in it.get("after", [])), default=-1)
    return d


def wrap(name, width=20):
    """Two lines at most, cut at a space."""
    lines, cur = [], ""
    for word in name.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    lines.append(cur)
    return lines[:1] + [" ".join(lines[1:])[:width - 1] + "…"] if len(lines) > 2 else lines


def diagram(items):
    """Columns by dependency depth; an arrow runs from each item to the items that wait on it."""
    d = depths(items)
    cols = {}
    for it in items:
        cols.setdefault(d[it["id"]], []).append(it)
    bw, bh, gx, gy = 180, 52, 56, 16
    pos = {}
    for c, col in cols.items():
        for r, it in enumerate(col):
            pos[it["id"]] = (c * (bw + gx), r * (bh + gy))
    w = len(cols) * (bw + gx) - gx
    h = max(len(c) for c in cols.values()) * (bh + gy) - gy
    o = [f'<svg viewBox="-2 -2 {w + 4} {h + 4}" width="{w + 4}" role="img" aria-label="Build order">',
         '<defs><marker id="ah" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8z" fill="var(--muted)"/></marker></defs>']
    for it in items:
        x, y = pos[it["id"]]
        for a in it.get("after", []):
            ax, ay = pos[a]
            x1, y1, x2, y2 = ax + bw, ay + bh / 2, x - 2, y + bh / 2
            o.append(f'<path class="e" d="M{x1} {y1}C{x1 + gx} {y1} {x2 - gx} {y2} {x2} {y2}" marker-end="url(#ah)"/>')
    for it in items:
        x, y = pos[it["id"]]
        lines = wrap(it["name"])
        top = y + bh / 2 - 8 * (len(lines) - 1) + 5
        spans = "".join(f'<tspan x="{x + 30}" y="{top + 16 * k}">{html.escape(t)}</tspan>' for k, t in enumerate(lines))
        o.append(f'<g><title>{html.escape(it["name"])}</title><rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="6"/>'
                 f'<text class="id" x="{x + 10}" y="{y + bh / 2 + 5}">{it["id"]}</text><text>{spans}</text></g>')
    return "".join(o) + "</svg>"


def spec_rows(s):
    lp = s.get("loop", {})
    return [("Outcome", s["outcome"]), ("Done when", s["done_when"]), ("Limits", s["limits"]),
            ("Output", s["output"]), ("Harness", s["harness"]),
            ("Loop", f'At most {lp.get("max")} tries. {lp.get("exit_when", "")}'),
            ("Verifier", s["verifier"]), ("Tools", ", ".join(s.get("tools", [])) or "none named"),
            ("Agent", f'{s.get("model", "?")}, {s.get("effort", "?")} effort'), ("Context", ", ".join(s.get("context", [])))]


def gaps_html(p, r):
    pt = p.get("patterns", {})
    if not p.get("gaps") and not pt:
        return []
    fired = ", ".join(pt.get("fired", [])) or "none"
    rows = "".join(f'<tr><td>{r(g["text"])}</td><td>{g["from"].replace("rule:", "rule: ")}</td><td>{g["owner"]}</td><td>{g["changes"]}</td></tr>' for g in p.get("gaps", []))
    return ["<h2>Gaps and edge cases</h2>",
            f'<p class="cap">Rule sets that fired: {fired}. Not fired: {", ".join(pt.get("not_fired", [])) or "none"}. Rules come from past tickets; a guess is a model prediction no one has checked.</p>',
            f'<div class="tbl"><table><thead><tr><th>Gap</th><th>From</th><th>Owner</th><th>Changes</th></tr></thead><tbody>{rows}</tbody></table></div>']


def render(p):
    r = Rich(p.get("legend", {}))
    oc = p["outcome"]
    items = p["items"]
    o = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
         f'<title>{html.escape(p["title"])}</title>{FONTS}<style>{CSS}{EXTRA}</style></head><body><main class="wrap">',
         f'<h1>{html.escape(p["title"])}</h1>',
         f'<p class="lede">Breakdown of: "{html.escape(p["ask"]["quote"])}"</p>',
         f'<div class="outcome"><p><b>Outcome.</b> {r(oc["outcome"])}</p><p><b>Done when.</b> {r(oc["done_when"])}</p><p><b>Limits.</b> {r(oc["limits"])}</p></div>',
         f'<p class="big">{r(p["big_picture"])}</p>',
         f'<div class="dia">{diagram(items)}</div><p class="cap">Arrows point from an item to the items that wait for it.</p>',
         '<div class="tbl"><table><thead><tr><th></th><th>Item</th><th>What it does</th><th>Size</th><th>After</th></tr></thead><tbody>']
    for it in items:
        cond = f' Only if {r(it["only_if"])}' if it.get("only_if") else ""
        if it is items[0]:
            cond = " Goes first." + cond
        o.append(f'<tr><td><b>{it["id"]}</b></td><td>{r(it["name"])}</td><td>{r(it["plain"])}{cond}</td><td>{it["size"]}</td><td>{", ".join(it.get("after", [])) or "start"}</td></tr>')
    o.append(f'</tbody></table></div><p class="cap">{KEY}</p>')
    o += gaps_html(p, r)
    o.append("<h2>Details</h2>")
    for it in items:
        rows = "".join(f"<tr><th>{k}</th><td>{r(v)}</td></tr>" for k, v in spec_rows(it["spec"]))
        dec = "".join(f'<li>{r(d["choice"])} Rejected: {r(", ".join(d["over"]))}. {r(d.get("because", ""))}<span class="lab">{d["label"]}</span></li>' for d in it.get("decisions", []))
        opn = "".join(f"<li>{r(q)}</li>" for q in it.get("open", []))
        o.append(f'<details><summary>{it["id"]}. {html.escape(it["name"])}</summary><div>'
                 f'<div class="tbl"><table><tbody>{rows}</tbody></table></div>'
                 + (f"<h3>Decisions</h3><ul>{dec}</ul>" if dec else "")
                 + (f"<h3>Open questions</h3><ul>{opn}</ul>" if opn else "") + "</div></details>")
    if p.get("log"):
        lg = "".join(f'<li><b>{e["item"]}</b>. {r(e["challenge"])} <span class="lab">{e["answer"]}</span> {r(e.get("because", ""))}</li>' for e in p["log"])
        o.append(f"<details><summary>Challenges so far</summary><div><ul>{lg}</ul></div></details>")
    if p.get("legend"):
        lgd = "".join(f"<div><b>{html.escape(k)}</b>. {html.escape(v)}</div>" for k, v in p["legend"].items())
        o.append(f'<details><summary>Words used here</summary><div class="legend">{lgd}</div></details>')
    o.append('<p class="ask">To go deeper, ask about one item by its letter, as in "more on B" or "why does C wait for B?". '
             'The answer covers that item only, and any change shows up on this page.</p></main></body></html>')
    return "\n".join(o)


def render_text(p):
    oc = p["outcome"]
    o = [p["title"], "", f'Outcome. {oc["outcome"]}', f'Done when. {oc["done_when"]}', f'Limits. {oc["limits"]}', "", p["big_picture"], ""]
    for it in p["items"]:
        o.append(f'{it["id"]}. {it["name"]} ({it["size"]}, after {", ".join(it.get("after", [])) or "nothing"}). {it["plain"]}')
        o += [f"  {k}. {v}" for k, v in spec_rows(it["spec"])]
        o += [f'  Decision. {d["choice"]} Rejected: {", ".join(d["over"])}. {d.get("because", "")} ({d["label"]})' for d in it.get("decisions", [])]
        o += [f'  Only if. {it["only_if"]}'] if it.get("only_if") else []
        o += [f"  Open. {q}" for q in it.get("open", [])]
    o += ["", "Gaps."] + [f'  {g["text"]} ({g["from"]}, {g["owner"]}, changes {g["changes"]})' for g in p.get("gaps", [])]
    o += ["", KEY, "", "Words used here."] + [f"  {k}. {v}" for k, v in p.get("legend", {}).items()]
    return "\n".join(o) + "\n"


def lc(t):
    first = t.split(" ", 1)[0]
    return t if len(first) > 1 and first.isupper() else t[:1].lower() + t[1:]


def render_prompt(p, iid):
    by = {it["id"]: it for it in p["items"]}
    it = by[iid]
    s, lp = it["spec"], it["spec"].get("loop", {})
    before = [f'- {a}. {by[a]["name"]}: {by[a]["spec"]["output"]}' for a in it.get("after", [])]
    return "\n".join([
        *([f'Run this only if {it["only_if"]} Otherwise report "not needed" and stop.'] if it.get("only_if") else []),
        f'Goal: {s["outcome"]} This is item {iid} of "{p["title"]}". The project outcome is: {p["outcome"]["outcome"]}',
        *(["Uses the output of:"] + before if before else []),
        f'Context: read only {", ".join(s.get("context", []))}. Ask before reading anything else.',
        f'Check: done when {lc(s["done_when"])}',
        f'Limits: {s["limits"]}',
        f'Output: {s["output"]}',
        f'Verify: run the {s["harness"]} until it passes. Then {lc(s["verifier"])} {NOT_PROOF} {EVIDENCE}',
        *([REVIEW] if s.get("harness") != "findings file" else []),
        f'Run on: {s.get("model")} at {s.get("effort")} effort.',
        f'If stuck: at most {lp.get("max")} tries. {lp.get("exit_when", "")}',
        'At the end: update RESUME.md with the goal, what is done and verified, the next step, key files and gotchas.',
        'Never say done or correct. Report what you ran and its output, and the verifier decides.',
        f'Tools: {", ".join(s.get("tools", [])) or "none named"}. Report only; push, post or message nothing unless the limits allow it.',
    ]) + "\n"


def main(argv):
    if argv[0] == "--prompt":
        print(render_prompt(json.load(open(argv[2], encoding="utf-8")), argv[1]), end="")
    elif argv[0] == "--text":
        print(render_text(json.load(open(argv[1], encoding="utf-8"))), end="")
    else:
        print(render(json.load(open(argv[0], encoding="utf-8"))))


if __name__ == "__main__":
    main(sys.argv[1:])
