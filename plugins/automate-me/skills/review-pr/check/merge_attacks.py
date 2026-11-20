"""Dedupe attack passes. A finding from either pass is kept.

Usage: python3 merge_attacks.py --out <attack.md> <pass.md> [<pass.md> ...]
Findings match on the file and the line. head/cap.py:3, ./cap.py:3 and
cap.py:3 are one finding. Wording and repro text do not split them. Both
passes' evidence is kept. A pass that does not parse is not an empty review:
the merge does not approve unless every pass parsed and none kept a finding.
Held lists every tried input that did not break.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import has_location, has_repro, norm, norm_where, parse_attack  # noqa: E402


def finding_key(finding):
    """Same normalized file and line. With no line, the same repro matches."""
    loc = norm_where(finding["where"])
    if loc:
        return ("where", loc)
    return ("repro", norm(finding["repro"]))


def merge(paths):
    """The merged review dict from pass files, in the order they were given."""
    docs, errors = [], []
    for path in paths:
        source = os.path.splitext(os.path.basename(path))[0]
        if not os.path.isfile(path):
            errors.append(source + ": missing pass")
            continue
        doc = parse_attack(path)
        doc["source"] = source
        docs.append(doc)
        if not doc["parsed"]:
            errors.append(source + ": " + (doc["errors"][0] if doc["errors"] else "unparseable output"))
    groups, order = {}, []
    for doc in docs:
        if not doc["parsed"]:
            continue
        for finding in doc["findings"]:
            if not finding["passes"]:
                finding["passes"] = [doc["source"]]
            if not finding.get("raw") and not has_location(finding) and not has_repro(finding):
                continue
            key = finding_key(finding)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(finding)
    kept = []
    for key in order:
        items = groups[key]
        claims, repros, observed, passes = [], [], "", []
        where = ""
        for item in items:
            loc = norm_where(item["where"])
            shown = f"{loc[0]}:{loc[1]}" if loc else item["where"]
            if not where or (loc and len(shown) < len(where)):
                where = shown
            agent = ", ".join(item["passes"]) or "pass"
            text = " ".join(item["claim"]).strip()
            if text:
                claims.append(f"{agent}: {text}")
            if has_repro(item) and item["repro"] not in repros:
                repros.append(item["repro"])
            if not observed and item["observed"] not in ("", "none"):
                observed = item["observed"]
            for name in item["passes"]:
                if name not in passes:
                    passes.append(name)
        kept.append({
            "where": where or items[0]["where"],
            "claim": claims or items[0]["claim"],
            "repro": " | ".join(repros),
            "observed": observed,
            "passes": passes,
        })
    broke = any(item["broke"] == "yes" for doc in docs if doc["parsed"] for item in doc["tried"])
    said_fixes = any(doc["parsed"] and doc["verdict"] == "needs fixes" for doc in docs)
    if kept or broke or said_fixes:
        verdict = "needs fixes"
    elif errors:
        verdict = ""
    else:
        verdict = "approve"
    tried, by_input = [], {}
    for doc in docs:
        if not doc["parsed"]:
            continue
        for item in doc["tried"]:
            if not item["input"] or not item["observed"]:
                continue
            key = item["input"]
            if key not in by_input:
                by_input[key] = {"input": item["input"], "observed": item["observed"], "broke": item["broke"]}
                tried.append(by_input[key])
            elif item["broke"] == "yes":
                by_input[key]["broke"] = "yes"
                by_input[key]["observed"] = item["observed"]
    title = docs[0]["title"] if docs else "Attack review"
    return {
        "title": title or "Attack review",
        "verdict": verdict,
        "tried": tried,
        "findings": kept,
        "held": [item for item in tried if item["broke"] == "no"],
        "errors": errors,
    }


def render(doc):
    """The merged review in the attack file shape."""
    lines = [f"# {doc['title']}", "", f"Verdict: {doc['verdict']}", "", "## Tried"]
    if not doc["tried"]:
        lines.append("")
    for item in doc["tried"]:
        lines += [f"- Input: {item['input']}", f"  Observed: {item['observed']}"]
        if item["broke"]:
            lines.append(f"  Broke: {item['broke']}")
        lines.append("")
    lines.append("## Findings")
    if not doc["findings"]:
        lines.append("")
    for i, finding in enumerate(doc["findings"], 1):
        passes = ", ".join(finding["passes"]) or "unspecified"
        lines.append(f"### F{i} | {finding['where']} | passes: {passes}")
        claims = [c for c in finding["claim"] if c.strip()]
        if claims:
            lines.extend(claims)
        else:
            lines.append("See the repro.")
        lines += [
            f"Repro: {finding['repro'] or 'none'}",
            f"Observed: {finding['observed'] or 'none'}",
            "",
        ]
    lines.append("## Held")
    if not doc["held"]:
        lines += ["None", ""]
    for item in doc["held"]:
        lines += [f"- Input: {item['input']}", f"  Observed: {item['observed']}", ""]
    return "\n".join(lines).rstrip() + "\n"


def main(argv):
    if any(a in ("-h", "--help") for a in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    if "--out" not in argv[1:]:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    out_at = argv.index("--out")
    if out_at + 1 >= len(argv):
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    out = argv[out_at + 1]
    skip = {out_at, out_at + 1}
    passes = [a for i, a in enumerate(argv) if i not in skip and i > 0 and not a.startswith("--")]
    if not passes:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    doc = merge(passes)
    if not doc["verdict"]:
        print("FAIL unparseable output, not an approve")
        for item in doc["errors"]:
            print(f"  {item}")
        return 1
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    open(out, "w").write(render(doc))
    if doc["errors"]:
        print("parsed with errors:")
        for item in doc["errors"]:
            print(f"  {item}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
