"""Checks a breakdown plan file: its shape, its limits and the writing rules.

Usage: python3 check_plan.py <plan.json>

Every plan string that lands in a rendered prompt (render_plan.prompt_fields: title, outcome.outcome,
each item's name, only_if, spec.outcome, done_when, output, limits, verifier, model, loop.exit_when,
tools and context), plus outcome.done_when and outcome.limits, must be one line of text and goes through
outcome's check_brief.judge. A placeholder or template hole fails (exit 1). A value that needs a person
prints an ASK line and exits 2 when nothing fails. Once the person says the value is real, add it to the
plan's `confirmed` map as `"<field>": "<value>"`, with the field as the ASK line names it, and rerun.
When the fields pass, each item's rendered prompt must also pass check_brief, so a plan that passes
renders prompts that pass. Exit 3 with one line on a usage error.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "outcome", "check"))
from check_brief import ask_lines, check as check_brief, judge  # noqa: E402
from render_plan import is_confirmed, prompt_fields, render_prompt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.join(HERE, "..", "shared")
LABELS = {"measured", "inferred", "guess"}
MAX_ITEMS = 8
MAX_LOOP = 10
MAX_WORDS = 900
MAX_OPEN = 2
MAX_GAPS = 8
MAX_GAP_WORDS = 250
FROM = {"evidence", "guess"}
OWNERS = {"pm", "engineer"}
EFFORTS = {"low", "medium", "high", "xhigh"}
ID = re.compile(r"^[A-Z]$")


def harness_kinds():
    with open(os.path.join(SHARED, "harness-kinds.md"), encoding="utf-8") as handle:
        text = handle.read()
    return set(re.findall(r"^\| `([^`]+)` \|", text, re.M))


def eng_patterns():
    d = os.path.join(SHARED, "rules", "eng")
    return {f[:-5] for f in os.listdir(d) if f.endswith(".json")} if os.path.isdir(d) else set()


def pm_sets():
    d = os.path.join(SHARED, "rules")
    return {f[:-5] for f in os.listdir(d) if f.endswith(".json")} if os.path.isdir(d) else set()


def check_gaps(p, ids, need):
    """Gaps sit outside the plan's word cap, with their own. Every engineering pattern is listed as fired or not."""
    pats = eng_patterns()
    pt = p.get("patterns", {})
    fired, skipped = set(pt.get("fired", [])), set(pt.get("not_fired", []))
    need(fired | skipped == pats, f"patterns must list every rule in shared/rules/eng as fired or not_fired: {sorted(pats)}")
    gaps = p.get("gaps", [])
    need(len(gaps) <= MAX_GAPS, f"{len(gaps)} gaps, limit {MAX_GAPS}; keep the ones that change an item")
    text = []
    for i, g in enumerate(gaps, 1):
        src = g.get("from", "")
        rule = src[5:] if src.startswith("rule:") else None
        need(src in FROM or rule in fired or (rule not in pats and rule in pm_sets()), f"gap {i}: from must be rule:<fired pattern or shared rule set>, evidence or guess")
        need(g.get("owner") in OWNERS, f"gap {i}: owner must be pm or engineer")
        need(g.get("changes") in ids or g.get("changes") == "question", f"gap {i}: changes must name an item, or say question")
        need(len(sentences(g.get("text", ""))) == 1, f"gap {i}: text must be one sentence")
        text.append(g.get("text", ""))
    words = len(" ".join(text).split())
    need(words <= MAX_GAP_WORDS, f"gaps are {words} words, limit {MAX_GAP_WORDS}")
    return text


def sentences(text):
    return [s for s in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"'`])", (text or "").strip()) if s]


def check(p):
    """Returns (errors, prose, words, asks)."""
    errs, prose, asks = [], [], []
    kinds = harness_kinds()
    seen_fields = set()

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    def real(value, where):
        """A field that reaches a prompt: one line of text, judged like a brief value."""
        if value in (None, "") or where in seen_fields:
            return
        seen_fields.add(where)
        if not isinstance(value, str):
            return need(False, f"{where} must be text, not {type(value).__name__}")
        need(len(f"x{value}x".splitlines()) == 1, f"{where} spans lines; the prompt needs it on one line")
        verdict, why = judge(value)
        need(verdict != "fail", f"{where} is a placeholder or holds a template hole")
        if verdict == "ask" and not is_confirmed(p, where, value):
            hole = ", or a hole to fill" if why == "hole" else ""
            asks.append(f"ASK: {where}: Is '{value}' a real answer for {where}{hole}?")

    confirmed = p.get("confirmed", {})
    need(isinstance(confirmed, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in confirmed.items()),
         'confirmed must map a field to its value, as {"item A spec.output": "ok"}')

    def one(text, where):
        need(len(sentences(text)) == 1, f"{where}: {len(sentences(text))} sentences, limit 1")

    need(p.get("title"), "title is missing")
    need(p.get("ask", {}).get("quote"), "ask.quote is missing; quote the request as written")
    for k in ("outcome", "done_when", "limits"):
        need(p.get("outcome", {}).get(k), f"outcome.{k} is missing")
        prose.append(p.get("outcome", {}).get(k, ""))
        real(p.get("outcome", {}).get(k), f"outcome.{k}")
    k = len(sentences(p.get("big_picture", "")))
    need(1 <= k <= 3, f"big_picture has {k} sentences, limit 3")
    prose.append(p.get("big_picture", ""))

    items = p.get("items", [])
    need(1 <= len(items) <= MAX_ITEMS, f"{len(items)} items, limit {MAX_ITEMS}; more means two projects, split the ask")
    seen = set()
    for it in items:
        i = it.get("id", "?")
        w = f"item {i}"
        need(ID.match(str(i)) and i not in seen, f"{w}: id must be one unused capital letter")
        for a in it.get("after", []):
            need(a in seen, f"{w}: after names {a}, which is not an earlier item")
        seen.add(i)
        need(it.get("name"), f"{w}: name is missing")
        one(it.get("plain", ""), f"{w} plain")
        need(it.get("size") in ("S", "M"), f"{w}: size {it.get('size')!r}; an L item must be split into S or M items")
        s = it.get("spec", {})
        need(s.get("tools"), f"{w}: spec.tools is empty; name the tools the agent needs")
        need(s.get("model"), f"{w}: spec.model is missing; name the model or role that runs it")
        need(s.get("effort") in EFFORTS, f"{w}: spec.effort must be low, medium, high or xhigh")
        need(s.get("context"), f"{w}: spec.context is empty; list the only files and outputs the agent gets")
        for f in ("outcome", "done_when", "limits", "output", "harness", "verifier"):
            need(s.get(f), f"{w}: spec.{f} is missing")
        need(all(isinstance(s.get(f, []), list) and all(isinstance(x, str) and x for x in s.get(f, [])) for f in ("tools", "context")),
             f"{w}: spec.tools and spec.context must be lists of text")
        for field, value, _ in prompt_fields(p, it):
            real(value, field)
        one(s.get("outcome", ""), f"{w} spec.outcome")
        need(s.get("harness") in kinds, f"{w}: harness {s.get('harness')!r} is not a kind in shared/harness-kinds.md")
        lp = s.get("loop", {})
        need(isinstance(lp.get("max"), int) and 1 <= lp["max"] <= MAX_LOOP, f"{w}: loop.max must be a whole number 1 to {MAX_LOOP}")
        need(lp.get("exit_when"), f"{w}: loop.exit_when is missing; say what happens at the cap")
        for d in it.get("decisions", []):
            need(d.get("label") in LABELS, f"{w}: decision {d.get('choice', '?')!r} needs label measured, inferred or guess")
            need(d.get("over"), f"{w}: decision {d.get('choice', '?')!r} names no rejected option")
            prose += [d.get("choice", ""), d.get("because", "")] + d.get("over", [])
        prose += [it.get("name", ""), it.get("plain", ""), it.get("only_if", "")] + it.get("open", [])
        prose += [s.get(f, "") for f in ("outcome", "done_when", "limits", "output", "verifier")] + [lp.get("exit_when", "")]

    gap_text = check_gaps(p, seen, need)
    n_open = sum(len(it.get("open", [])) for it in items)
    need(n_open <= MAX_OPEN, f"{n_open} open questions, limit {MAX_OPEN}; keep only those whose answer changes an item")
    words = len(" ".join(x for x in prose if isinstance(x, str) and x).split())
    need(words <= MAX_WORDS, f"plan prose is {words} words, limit {MAX_WORDS}; cut decisions and limits before items")

    for e in p.get("log", []):
        need(e.get("item") in seen, f"log entry names unknown item {e.get('item')!r}")
        need(e.get("answer") in ("held", "changed"), "log answer must be held or changed")
        prose += [e.get("challenge", ""), e.get("because", "")]

    legend = p.get("legend") if isinstance(p.get("legend"), dict) else {}
    body = "\n".join(x for x in prose if isinstance(x, str) and x).lower()
    for term, definition in legend.items():
        need(re.search(r"(?<![\w-])" + re.escape(term.lower()) + r"(?:s|es|d|ed|ing)?(?![\w-])", body), f"legend term '{term}' is never used")
        prose.append(definition)
    if not errs:
        for it in items:
            body = render_prompt(p, it["id"])
            errs += [f"item {it['id']} prompt fails check_brief: {f}" for _, fails in check_brief(body) for f in fails]
            asks += [] if asks else [f"ASK: item {it['id']} prompt: {line[5:]}" for line in ask_lines(body)]
    return errs, [x for x in prose if isinstance(x, str) and x] + gap_text, words, asks


def main(argv):
    if argv in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    if len(argv) != 1:
        print("usage: python3 check_plan.py <plan.json>", file=sys.stderr)
        return 3
    path = argv[0]
    try:
        with open(path, encoding="utf-8") as handle:
            p = json.load(handle)
    except (OSError, ValueError) as err:
        print(f"usage: cannot read {path}: {err}", file=sys.stderr)
        return 3
    if not isinstance(p, dict):
        print("FAIL plan: the plan must be a JSON object; see references/plan-shape.md")
        return 1
    try:
        errs, prose, words, asks = check(p)
    except (AttributeError, TypeError, KeyError) as err:
        print(f"FAIL plan: a field has the wrong type ({err}); see references/plan-shape.md")
        return 1
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(prose))
    out = subprocess.run([sys.executable, os.path.join(SHARED, "check_writing.py"), f.name], capture_output=True, text=True)
    os.unlink(f.name)
    for e in errs:
        print("FAIL plan:", e)
    if out.returncode:
        for ln in out.stdout.strip().splitlines():
            hit = re.search(r"line (\d+)", ln)
            print(ln + (f"\n    > {prose[int(hit.group(1)) - 1]}" if hit and int(hit.group(1)) <= len(prose) else ""))
    for a in asks:
        print(a)
    if errs or out.returncode:
        return 1
    if asks:
        return 2
    print(f"PASS plan: {len(p['items'])} items, {words} words of {MAX_WORDS}, writing clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
