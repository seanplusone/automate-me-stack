"""Run: python3 check/test_merge_attacks.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import check_attack, parse_attack  # noqa: E402
from merge_attacks import merge, render  # noqa: E402

FAILS = []


def write(name, text):
    path = os.path.join(tempfile.mkdtemp(), name)
    open(path, "w").write(text)
    return path


def passage(agent, where, repro, observed, broke="yes", claim="accept returns True for a failed case."):
    return "\n".join([
        "# Attack review: sample",
        "",
        "Verdict: needs fixes",
        "",
        "## Tried",
        f"- Input: {repro}",
        f"  Observed: {observed}",
        f"  Broke: {broke}",
        "- Input: {\"passed\": false}",
        "  Observed: False",
        "  Broke: no",
        "",
        "## Findings",
        f"### F1 | {where} | passes: {agent}",
        claim,
        f"Repro: {repro}",
        f"Observed: {observed}",
        "",
        "## Held",
        "- Input: {\"passed\": false}",
        "  Observed: False",
        "",
    ])


def expect(name, got, want):
    if got != want:
        FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


one = merge([write("a.md", passage("current", "report.py:4", "{\"ok\": false}", "True"))])
expect("one pass keeps the finding", len(one["findings"]), 1)
expect("one pass needs fixes", one["verdict"], "needs fixes")
expect("one pass lists what held", [item["input"] for item in one["held"]], ["{\"passed\": false}"])

shared = "{\"ok\": false}"
kept = merge([
    write("a.md", passage("codex", "report.py:4", shared, "True")),
    write("b.md", passage("claude", "report.py:4", shared, "True")),
])
expect("two passes keep a shared line", len(kept["findings"]), 1)
expect("passes are unioned", kept["findings"][0]["passes"], ["codex", "claude"])

split = merge([
    write("a.md", passage("codex", "report.py:4", shared, "True")),
    write("b.md", passage("claude", "cap.py:3", "within_cap(5)", "False", claim="within_cap returns False for 5.")),
])
expect("either pass keeps its own line", len(split["findings"]), 2)
expect("either pass needs fixes", split["verdict"], "needs fixes")

same_repro = merge([
    write("a.md", passage("codex", "none", "bug line bug line", "True", claim="passes returns True.")),
    write("b.md", passage("claude", "none", "bug line bug line", "True", claim="passes returns True.")),
])
expect("same repro with no line is one finding", len(same_repro["findings"]), 1)

first = passage("current", "score_review.py:6", "bug line bug line", "True", claim="passes returns True.")
second = (
    "### F2 | score_review.py:6 | passes: current\n"
    "passes returns False for a real note.\n"
    "Repro: accept returns True at report.py:4 for input x\n"
    "Observed: False\n\n"
)
both = merge([write("c.md", first.replace("## Held", second + "## Held"))])
expect("two repros on one line are one finding", len(both["findings"]), 1)
expect("both repros are kept", "bug line bug line" in both["findings"][0]["repro"] and "report.py:4" in both["findings"][0]["repro"], True)

paths = merge([
    write("a.md", passage("codex", "head/cap.py:3", "within_cap(5)", "False", claim="The cap rejects 5.")),
    write("b.md", passage("claude", "./cap.py:3", "call(5)", "False", claim="Five is outside the cap.")),
])
expect("head and dot prefixes match", len(paths["findings"]), 1)
expect("path merge needs fixes", paths["verdict"], "needs fixes")
expect("both agents stay on the finding", paths["findings"][0]["passes"], ["codex", "claude"])
expect("normalized where", paths["findings"][0]["where"], "cap.py:3")

cased = merge([
    write("a.md", passage("codex", "cases/item-cap/head/cap.py:3", "within_cap(5)", "False")),
    write("b.md", passage("claude", "cap.py:3", "n == 5", "False", claim="off by one")),
])
expect("a case directory prefix matches", len(cased["findings"]), 1)

garbage = write("bad.md", "Ship it. The diff looks correct.\n")
clean = write("clean.md", "\n".join([
    "# Attack review: clean", "", "Verdict: approve", "", "## Tried",
    "- Input: empty", "  Observed: ok", "  Broke: no", "", "## Findings", "", "## Held",
    "- Input: empty", "  Observed: ok", "",
]))
bad = merge([garbage, clean])
expect("unparseable output is not an approve", bad["verdict"], "")
timed = write("codex.md", "Parse: timeout\n")
found = write("claude.md", passage("claude", "head/cap.py:3", "within_cap(5)", "False"))
late = merge([timed, found])
expect("a timeout does not drop the other bug", late["verdict"], "needs fixes")
expect("the surviving where is kept", late["findings"][0]["where"], "cap.py:3")
other = write("other.md", "\n".join([
    "# Attack review: clean", "", "Verdict: approve", "", "## Tried",
    "- Input: empty", "  Observed: ok", "  Broke: no", "", "## Findings", "", "## Held",
    "- Input: empty", "  Observed: ok", "",
]))
expect("two clean passes approve", merge([clean, other])["verdict"], "approve")

text = render(one)
path = write("merged.md", text)
expect("merged file passes the checker", check_attack(path), [])
parsed = parse_attack(path)
expect("round trip keeps the verdict", parsed["verdict"], "needs fixes")
expect("round trip keeps the finding line", parsed["findings"][0]["where"], "report.py:4")

if __name__ == "__main__":
    for item in FAILS:
        print(f"FAIL {item}")
    total = 22
    print(f"{total - len(FAILS)}/{total} passed")
    sys.exit(1 if FAILS else 0)
