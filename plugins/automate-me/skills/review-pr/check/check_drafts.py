"""Checks out/drafts.md against the format in ../SKILL.md, then the shared writing rules.

Usage: python3 check_drafts.py <drafts.md>
Exits 1 if anything fails.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from check_writing import check_writing, report  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from classify import HASHED, summary  # noqa: E402

TAGS = {"blocking", "should fix", "question", "nit"}
MAX_COMMENT_WORDS = 50
MAX_EVIDENCE_WORDS = 25
MAX_PLAIN_WORDS = 110
MAX_STEP_WORDS = 20
MIN_STEPS, MAX_STEPS = 2, 6
STEP_LABELS = {"measured", "inferred"}
MAX_FINDINGS = 5
MAX_NITS = 1
VERDICT = re.compile(r"^(approve|approve after .+|needs answer: .+|hold: .+|scope: .+)$")
PR_HEAD = re.compile(r"^## (\S+/\S+#\d+) \| (.+)$")
FINDING_HEAD = re.compile(r"^### (.+?) \| (\S+:\d+|PR) \| (https://\S+)(?: \| reply \d+)?$")
SITES = re.compile(r"^\d+ \| \S.*$")
MID_COLON = re.compile(r"[a-z`)\]] *: +[a-z`\"]")
MD_LINK = re.compile(r"\[([^\]]+)\]\(https?://[^)\s]+\)")
BARE_REF = re.compile(r"(?<![\w/@.#-])(?:[\w.-]+/)?[\w.-]*#\d+\b|(?<![\w/#.-])[0-9a-f]{7,40}\b")


def unlinked_refs(comment):
    """PR, issue and commit references left as bare text, outside code spans, links and URLs."""
    text = re.sub(r"`[^`]*`", "", comment)
    text = MD_LINK.sub("", text)
    text = re.sub(r"https?://\S+", "", text)
    refs = [m.group(0) for m in BARE_REF.finditer(text)]
    return [r for r in refs if "#" in r or (re.search(r"\d", r) and re.search(r"[a-f]", r))]


def comment_words(comment):
    """Words in a comment, counting each markdown link as one."""
    return len(MD_LINK.sub("link", comment).split())


def read(path):
    """The whole drafts file: title, summary, PR sections with their findings, and the Refuter line."""
    doc = {"title": "", "summary": [], "prs": [], "refuter": "", "totals": False}
    prs, finding = [], None
    for raw in open(path):
        line = raw.rstrip("\n")
        if line.startswith("# ") and not doc["title"]:
            doc["title"] = line[2:].strip()
            continue
        if line.startswith("## Totals"):
            finding = None
            prs.append(None)
            continue
        if line.startswith("Refuter:"):
            doc["refuter"] = line
            doc["totals"] = bool(re.match(r"^Refuter: checked \d+, reworded \d+, dropped \d+\.$", line))
            continue
        m = PR_HEAD.match(line)
        if m:
            prs.append({"pr": m.group(1), "verdict": m.group(2), "about": "", "changes": "", "body": "", "findings": []})
            finding = None
            continue
        if line.startswith("### ") and prs and prs[-1]:
            m = FINDING_HEAD.match(line)
            finding = {"head": line, "match": m, "comment": [], "evidence": [], "sites": [], "plain": [], "steps": [], "bad_steps": []}
            prs[-1]["findings"].append(finding)
            continue
        if not prs:
            if line.strip():
                doc["summary"].append(line.strip())
            continue
        if line.startswith("Body:"):
            if prs[-1]:
                prs[-1]["body"] = line[len("Body:"):].strip()
            finding = None
            continue
        if line.startswith("About:") and finding is None and prs[-1]:
            prs[-1]["about"] = line[len("About:"):].strip()
            continue
        if line.startswith("Changes:") and finding is None and prs[-1]:
            prs[-1]["changes"] = line[len("Changes:"):].strip()
            continue
        if finding is None or not line.strip():
            continue
        if line.startswith("Sites:"):
            finding["sites"].append(line[len("Sites:"):].strip())
        elif line.startswith("Evidence:"):
            finding["evidence"].append(line[len("Evidence:"):].strip())
        elif line.startswith("Plain:"):
            finding["plain"].append(line[len("Plain:"):].strip())
        elif line.startswith("Step:"):
            label, sep, text = line[len("Step:"):].strip().partition(" | ")
            if sep and label in STEP_LABELS and text.strip():
                finding["steps"].append((label, text.strip()))
            else:
                finding["bad_steps"].append(line[len("Step:"):].strip())
        else:
            finding["comment"].append(line.strip())
    doc["prs"] = [p for p in prs if p]
    return doc


def parse(path):
    """Returns PR sections, each with its verdict and findings, plus whether a Totals line exists."""
    doc = read(path)
    return doc["prs"], doc["totals"]


def read_classes(path):
    """The classes.json beside drafts.md as a dict, or None when there is none."""
    classes = os.path.join(os.path.dirname(os.path.abspath(path)), "classes.json")
    return json.load(open(classes)) if os.path.exists(classes) else None


def is_generated(classes, pr, anchor):
    """Whether an anchored path is generated, by classes.json when it lists the PR, else by its name."""
    listed = (classes or {}).get(pr, {}).get("files", {})
    if anchor in listed:
        return listed[anchor] == "generated"
    return bool(HASHED.search(anchor.rsplit("/", 1)[-1])) or anchor.endswith(".gz")


def check_drafts(path):
    prs, totals = parse(path)
    classes = read_classes(path)
    fails = []
    if not prs:
        fails.append("no '## <owner>/<repo>#<n> | <verdict>' section")
    for pr in prs:
        name = pr["pr"]
        if not VERDICT.match(pr["verdict"]):
            fails.append(f"{name} verdict must be 'approve', 'approve after <x>', 'needs answer: <question>', 'hold: <reason>' or 'scope: <what was checked>': {pr['verdict']}")
        if classes is not None:
            want = summary(name, classes[name]["files"]).partition(": ")[2] if name in classes else None
            if not pr["changes"]:
                fails.append(f"{name} missing the 'Changes:' line; paste what check/classify.py printed after the colon")
            elif want and pr["changes"] != want:
                fails.append(f"{name} Changes line does not match classes.json: want '{want}'")
        tags = []
        seen = set()
        for f in pr["findings"]:
            m = f["match"]
            if not m:
                fails.append(f"{name} heading must be '### <tag> | <path>:<line> or PR | <url>[ | reply <comment id>]': {f['head'][:70]}")
                continue
            tag, site = m.group(1), m.group(2)
            where = f"{name} {site}"
            tags.append(tag)
            if site != "PR" and is_generated(classes, name, site.rsplit(":", 1)[0]):
                fails.append(f"{where} anchored on a generated file; put a bundle ask in the review body and a code ask on the source PR")
            if tag not in TAGS:
                fails.append(f"{where} unknown tag '{tag}'")
            comment = " ".join(f["comment"])
            words = comment_words(comment)
            bare = unlinked_refs(comment)
            if bare:
                fails.append(f"{where} link every PR, issue and commit it names: {', '.join(bare)}")
            if words == 0:
                fails.append(f"{where} no comment text")
            if words > MAX_COMMENT_WORDS:
                fails.append(f"{where} comment is {words} words, max {MAX_COMMENT_WORDS}; cut a clause, not the articles (W11)")
            if MID_COLON.search(re.sub(r"https?://\S+", "", comment)):
                fails.append(f"{where} W2 colon joining two halves of a sentence")
            if len(f["evidence"]) > 1:
                fails.append(f"{where} more than one Evidence line")
            if len(f["sites"]) > 1:
                fails.append(f"{where} more than one Sites line")
            if len(f["plain"]) > 1:
                fails.append(f"{where} more than one Plain line")
            for pl in f["plain"]:
                if len(pl.split()) > MAX_PLAIN_WORDS:
                    fails.append(f"{where} plain is {len(pl.split())} words, max {MAX_PLAIN_WORDS}")
            first = comment not in seen
            seen.add(comment)
            for bad in f["bad_steps"]:
                fails.append(f"{where} Step line must be 'Step: measured | <text>' or 'Step: inferred | <text>': {bad[:60]}")
            for _, text in f["steps"]:
                if len(text.split()) > MAX_STEP_WORDS:
                    fails.append(f"{where} step is {len(text.split())} words, max {MAX_STEP_WORDS}: {text[:40]}")
            n = len(f["steps"])
            if tag == "nit" and n:
                fails.append(f"{where} nit carries {n} steps, nits take none")
            elif first and tag in ("blocking", "should fix") and not MIN_STEPS <= n <= MAX_STEPS:
                fails.append(f"{where} {tag} needs {MIN_STEPS} to {MAX_STEPS} Step lines on its first copy, has {n}")
            elif tag == "question" and n and not MIN_STEPS <= n <= MAX_STEPS:
                fails.append(f"{where} question takes {MIN_STEPS} to {MAX_STEPS} Step lines or none, has {n}")
            for st in f["sites"]:
                if not SITES.match(st):
                    fails.append(f"{where} Sites line must be '<n> | <command>': {st[:60]}")
            for ev in f["evidence"]:
                if len(ev.split()) > MAX_EVIDENCE_WORDS:
                    fails.append(f"{where} evidence is {len(ev.split())} words, max {MAX_EVIDENCE_WORDS}")
        holds = pr["verdict"].startswith("hold:")
        if holds and "blocking" not in tags:
            fails.append(f"{name} verdict is hold with no blocking finding")
        if not holds and "blocking" in tags:
            fails.append(f"{name} has a blocking finding but the verdict does not hold")
        if pr["verdict"].startswith("approve") and tags and not pr["body"]:
            fails.append(f"{name} approves with comments, so the Body line must say the approval stands with comments inline")
        sites = {}
        for f in pr["findings"]:
            if f["match"]:
                sites.setdefault(" ".join(f["comment"]), f["match"].group(1))
        if len(sites) > MAX_FINDINGS:
            fails.append(f"{name} has {len(sites)} findings, max {MAX_FINDINGS} (same text at several lines counts once)")
        nits = len({c for c, t in sites.items() if t == "nit"})
        if nits > MAX_NITS:
            fails.append(f"{name} has {nits} nit comments, fold them into one")
    if not totals:
        fails.append("missing '## Totals' with 'Refuter: checked <n>, reworded <n>, dropped <n>.'")
    report(f"drafts: {path}", fails)
    return fails


if __name__ == "__main__":
    from cli import usage_or_exit
    usage_or_exit(__doc__, sys.argv, 1)
    bad = check_drafts(sys.argv[1])
    bad += check_writing(sys.argv[1])
    sys.exit(1 if bad else 0)
