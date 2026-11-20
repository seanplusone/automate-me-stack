"""Dedupe attack passes and keep only findings another pass reproduced.

Usage: python3 merge_attacks.py --out <attack.md> <pass.md> [<pass.md> ...]
With one pass, every finding that has a file:line or a repro is kept.
With two or more, a finding is kept only when at least two passes report it.
The same file, line and repro is one finding. With no repro, the same file
and line is one finding. With no line, the same repro is one finding. The verdict is
needs fixes when a finding remains, and approve when none do. Held lists
every tried input that did not break.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import has_location, has_repro, norm, parse_attack  # noqa: E402


def finding_key(finding):
    """Same line and same repro match. A second repro on that line stays separate."""
    if has_location(finding) and has_repro(finding):
        return ("both", finding["where"], norm(finding["repro"]))
    if has_location(finding):
        return ("where", finding["where"])
    return ("repro", norm(finding["repro"]))


def merge(paths):
    """The merged review dict from pass files, in the order they were given."""
    docs = [parse_attack(path) for path in paths]
    groups, order = {}, []
    for doc in docs:
        seen = set()
        for finding in doc["findings"]:
            if not has_location(finding) and not has_repro(finding):
                continue
            key = finding_key(finding)
            if key in seen:
                continue
            seen.add(key)
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(finding)
    kept = []
    for key in order:
        items = groups[key]
        if len(docs) >= 2 and len(items) < 2:
            continue
        base = {
            "where": items[0]["where"],
            "claim": items[0]["claim"],
            "repro": items[0]["repro"],
            "observed": items[0]["observed"],
            "passes": [],
        }
        for item in items:
            if has_repro(item):
                base["repro"] = item["repro"]
                base["observed"] = item["observed"]
            for name in item["passes"]:
                if name not in base["passes"]:
                    base["passes"].append(name)
        kept.append(base)
    tried, by_input = [], {}
    for doc in docs:
        for item in doc["tried"]:
            if not item["input"] or not item["observed"]:
                continue
            key = norm(item["input"])
            if key not in by_input:
                by_input[key] = {"input": item["input"].strip(), "observed": item["observed"], "broke": item["broke"]}
                tried.append(by_input[key])
            elif item["broke"] == "yes":
                by_input[key]["broke"] = "yes"
                by_input[key]["observed"] = item["observed"]
    title = docs[0]["title"] if docs else "Attack review"
    return {
        "title": title or "Attack review",
        "verdict": "needs fixes" if kept else "approve",
        "tried": tried,
        "findings": kept,
        "held": [item for item in tried if item["broke"] == "no"],
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
        claim = " ".join(finding["claim"]).strip() or "See the repro."
        lines += [
            f"### F{i} | {finding['where']} | passes: {passes}",
            claim,
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
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    open(out, "w").write(render(merge(passes)))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
