"""Union attack passes that end in a JSON block.

Usage: python3 merge_attacks.py --out <attack.md> [--] <pass.md> [...]
Findings on the same normalized file and line are one finding. A null line
is kept on its own and is never dropped. Both passes' claims are kept.
A merged approve requires every pass to be a valid approve. Invalid JSON
is an error and is never an approve. A file named --x.md must follow --.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import common_suffix, norm_span, path_suffix, parse_attack  # noqa: E402


def _blank(source):
    return {
        "parsed": False, "tried": [], "findings": [], "verdict": "", "stated": "",
        "source": source, "errors": ["missing pass"],
    }


def merge(paths):
    """The merged review dict. verdict is approve, needs fixes, or "" when it must not approve."""
    docs, errors = [], []
    for path in paths:
        source = os.path.splitext(os.path.basename(path))[0]
        if not os.path.isfile(path):
            errors.append(source + ": missing pass")
            docs.append(_blank(source))
            continue
        doc = parse_attack(path)
        doc["source"] = source
        docs.append(doc)
        if not doc["parsed"]:
            errors.append(source + ": " + (doc["errors"][0] if doc["errors"] else "unparseable output"))
    groups, order, nulls = [], [], []
    tried, by_input = [], {}
    for doc in docs:
        if not doc["parsed"]:
            continue
        for item in doc["tried"]:
            key = item["input"]
            if key not in by_input:
                by_input[key] = {"input": item["input"], "broke": item["broke"], "observed": item["observed"]}
                tried.append(by_input[key])
            elif item["broke"]:
                by_input[key]["broke"] = True
                by_input[key]["observed"] = item["observed"]
        for finding in doc["findings"]:
            try:
                path, start, end = norm_span(finding["file"], finding["line"])
            except ValueError:
                errors.append(doc["source"] + ": line out of range")
                continue
            stored = {
                "file": path, "line": start, "claim": finding["claim"], "repro": finding["repro"],
                "passes": [doc["source"]],
            }
            if start is None:
                nulls.append(stored)
                continue
            placed = None
            for group in groups:
                if group["start"] == start and group["end"] == end and path_suffix(group["path"], path):
                    placed = group
                    break
            if placed is None:
                placed = {"path": path, "start": start, "end": end, "items": []}
                groups.append(placed)
                order.append(placed)
            placed["items"].append(stored)
            placed["path"] = common_suffix(placed["path"], path) or placed["path"]
    findings = []
    for key in order:
        items = key["items"]
        key_path = key["path"]
        claims, repros, passes = [], [], []
        for item in items:
            agent = item["passes"][0]
            if item["claim"]:
                claims.append(f"{agent}: {item['claim']}")
            if item["repro"] and item["repro"] not in repros:
                repros.append(item["repro"])
            for name in item["passes"]:
                if name not in passes:
                    passes.append(name)
        findings.append({
            "file": key_path,
            "line": items[0]["line"],
            "claim": " | ".join(claims),
            "repro": " | ".join(repros),
            "passes": passes,
        })
    findings.extend(nulls)
    parsed = [doc for doc in docs if doc["parsed"]]
    needs = any(doc["verdict"] == "needs fixes" for doc in parsed) or bool(findings) or any(
        item["broke"] for item in tried)
    if parsed and all(doc["verdict"] == "approve" for doc in parsed) and not errors and not needs:
        verdict = "approve"
    elif needs:
        verdict = "needs fixes"
    else:
        verdict = ""
    title = "Attack review"
    return {
        "title": title,
        "verdict": verdict,
        "tried": tried,
        "findings": findings,
        "errors": errors,
    }


def render(doc):
    """Markdown summary plus one json block. The checker reads the json."""
    data = {
        "verdict": doc["verdict"],
        "tried": [
            {"input": item["input"], "broke": bool(item["broke"]), "observed": item["observed"]}
            for item in doc["tried"]
        ],
        "findings": [
            {"file": item["file"], "line": item["line"], "claim": item["claim"], "repro": item["repro"]}
            for item in doc["findings"]
        ],
    }
    lines = [
        f"# {doc['title']}",
        "",
        f"Verdict: {doc['verdict']}",
        "",
        "```json",
        json.dumps(data, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv):
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    out, passes, ended = None, [], False
    index = 1
    while index < len(argv):
        arg = argv[index]
        if ended:
            passes.append(arg)
        elif arg == "--":
            ended = True
        elif arg == "--out":
            if out is not None:
                print("repeated --out", file=sys.stderr)
                return 2
            if index + 1 >= len(argv):
                print((__doc__ or "").strip(), file=sys.stderr)
                return 2
            out = argv[index + 1]
            index += 1
        elif arg.startswith("--"):
            print(f"unknown option {arg}. Put pass files after --", file=sys.stderr)
            return 2
        else:
            passes.append(arg)
        index += 1
    if not out or not passes:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2
    doc = merge(passes)
    if not doc["verdict"]:
        if os.path.isfile(out):
            os.remove(out)
        print("FAIL unparseable output, not an approve")
        for item in doc["errors"]:
            print(f"  {item}")
        return 1
    directory = os.path.dirname(os.path.abspath(out)) or "."
    os.makedirs(directory, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", dir=directory, prefix=".merge-", delete=False)
    try:
        handle.write(render(doc))
        handle.close()
        os.replace(handle.name, out)
    except Exception:
        handle.close()
        if os.path.exists(handle.name):
            os.remove(handle.name)
        raise
    if doc["errors"]:
        print("parsed with errors:")
        for item in doc["errors"]:
            print(f"  {item}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
