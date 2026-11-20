"""Check an attack review: inputs were run, findings are locatable, planted bugs are not approved.

Usage: python3 check_attack.py <attack.md> [--key <key.md>]
Exits 1 if the review tried nothing, a finding has neither a file:line nor a
repro with observed output, a tried input that held is missing from Held, or
the verdict is approve while the key says Planted: yes.
"""
import os
import re
import sys

VERDICT = re.compile(r"^Verdict: (approve|needs fixes)$")
ITEM = re.compile(r"^- Input: (.+)$")
INDENT_OBS = re.compile(r"^  Observed: (.*)$")
INDENT_BROKE = re.compile(r"^  Broke: (yes|no)$")
FINDING = re.compile(r"^### (\S+) \| (\S+) \| passes: (.+)$")
REPRO = re.compile(r"^Repro: (.*)$")
OBS = re.compile(r"^Observed: (.*)$")
WHERE = re.compile(r"^\S+:\d+$")


def norm(text):
    return re.sub(r"\s+", " ", text.strip())


def planted_bug(path):
    """True when the key marks a case that hides a bug the review must not approve."""
    for line in open(path):
        if line.strip().lower() == "planted: yes":
            return True
    return False


def catch_terms(path):
    """Catch terms from a `Catch:` line. A term written a/b matches either side."""
    terms = []
    for line in open(path):
        m = re.match(r"^Catch:\s*(.+)$", line.strip())
        if m:
            terms = [t.strip() for t in m.group(1).split("|") if t.strip()]
    return terms


def has_location(finding):
    return bool(WHERE.fullmatch(finding["where"]))


def has_repro(finding):
    return finding["repro"] not in ("", "none") and finding["observed"] not in ("", "none")


def parse_attack(path):
    """An attack file: verdict, tried inputs, findings, and inputs that held."""
    doc = {"title": "", "verdict": "", "tried": [], "findings": [], "held": []}
    section, cur = None, None
    for raw in open(path):
        line = raw.rstrip("\n")
        if line.startswith("# ") and not line.startswith("## "):
            doc["title"] = line[2:].strip()
            continue
        m = VERDICT.match(line.strip())
        if m and doc["verdict"] == "":
            doc["verdict"] = m.group(1)
            continue
        if line.strip() == "## Tried":
            section, cur = "tried", None
            continue
        if line.strip() == "## Findings":
            section, cur = "findings", None
            continue
        if line.strip() == "## Held":
            section, cur = "held", None
            continue
        if section in ("tried", "held"):
            m = ITEM.match(line)
            if m:
                cur = {"input": m.group(1).strip(), "observed": "", "broke": ""}
                doc[section].append(cur)
                continue
            if cur is None:
                continue
            m = INDENT_OBS.match(line)
            if m:
                cur["observed"] = m.group(1).strip()
                continue
            m = INDENT_BROKE.match(line)
            if m and section == "tried":
                cur["broke"] = m.group(1)
            continue
        if section != "findings":
            continue
        m = FINDING.match(line)
        if m:
            cur = {
                "id": m.group(1),
                "where": m.group(2),
                "passes": [p.strip() for p in m.group(3).split(",") if p.strip()],
                "claim": [],
                "repro": "",
                "observed": "",
            }
            doc["findings"].append(cur)
            continue
        if cur is None:
            continue
        m = REPRO.match(line)
        if m:
            cur["repro"] = m.group(1).strip()
            continue
        m = OBS.match(line)
        if m:
            cur["observed"] = m.group(1).strip()
            continue
        if line.strip():
            cur["claim"].append(line.strip())
    return doc


def check_attack(path, key_path=None):
    """Fail strings for one attack file. Empty means it passed."""
    doc = parse_attack(path)
    fails = []
    tried = [t for t in doc["tried"] if t["input"] and t["observed"]]
    if not tried:
        fails.append("zero breaking inputs tried")
    if doc["verdict"] not in ("approve", "needs fixes"):
        fails.append("verdict must be approve or needs fixes")
    for finding in doc["findings"]:
        if not has_location(finding) and not has_repro(finding):
            fails.append(f"{finding['id']} has no location and no repro")
    held = {norm(item["input"]) for item in doc["held"] if item["input"]}
    for item in tried:
        if item["broke"] == "no" and norm(item["input"]) not in held:
            fails.append("held list omits an input that did not break: " + item["input"])
    if key_path and planted_bug(key_path) and doc["verdict"] == "approve":
        fails.append("approve on a case with a planted bug")
    return fails


def main(argv):
    from cli import usage_or_exit
    if any(a in ("-h", "--help") for a in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    args = []
    key = None
    i = 1
    while i < len(argv):
        if argv[i] == "--key":
            if i + 1 >= len(argv):
                usage_or_exit(__doc__, ["check_attack.py"], 1)
            key = argv[i + 1]
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if len(args) != 1:
        usage_or_exit(__doc__, ["check_attack.py"], 1)
    fails = check_attack(args[0], key)
    print(f"{'FAIL' if fails else 'PASS'} attack: {os.path.basename(args[0])}")
    for item in fails:
        print(f"  {item}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
