"""Check an attack review: inputs were run, findings are locatable, planted bugs are not approved.

Usage: python3 check_attack.py <attack.md> [--key <key.md>]
Exits 1 if the review does not parse, tried nothing, a finding has neither a
file:line nor a repro with observed output, a tried input that held is missing
from Held, or the verdict is approve while the case key says Planted: yes.
When --key is omitted, a key.md above the attack file, inside a cases
directory, is used.
"""
import os
import re
import sys

VERDICT = re.compile(r"^Verdict:\s*(approve|needs fixes)\b", re.I)
ITEM = re.compile(r"^[-*]\s+Input:\s*(.+)$", re.I)
OBS = re.compile(r"^\s*Observed:\s*(.*)$", re.I)
BROKE = re.compile(r"^\s*Broke:\s*(yes|no)\b", re.I)
FINDING = re.compile(r"^###\s+(\S+)\s*\|\s*(\S+?)(?:\s*\|\s*passes:\s*(.*))?$")
REPRO = re.compile(r"^Repro:\s*(.*)$", re.I)
WHERE = re.compile(r"^\S+:\d+$")
PARSE_LINE = re.compile(r"^Parse:\s*\S", re.I)


def norm(text):
    return re.sub(r"\s+", " ", text.strip())


def soften(text):
    """Lower case, then drop quotes and backticks so phrasing still matches."""
    text = text.lower().replace("`", "")
    text = re.sub(r"[\"']", "", text)
    return re.sub(r"\s+", " ", text).strip()


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


def norm_where(where):
    """(path, line) with ./, cases/<name>/, and head or base prefixes removed."""
    if not where or where == "none" or ":" not in where:
        return None
    path, line = where.rsplit(":", 1)
    if not re.fullmatch(r"\d+", line):
        return None
    path = path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    parts = [part for part in path.split("/") if part not in ("", ".")]
    if len(parts) >= 3 and parts[0] == "cases":
        parts = parts[2:]
    last = None
    for i, part in enumerate(parts):
        if part in ("head", "base"):
            last = i
    if last is not None:
        parts = parts[last + 1:]
    if not parts:
        return None
    return ("/".join(parts), line)


def same_where(left, right):
    a, b = norm_where(left), norm_where(right)
    return a is not None and a == b


def find_key(attack_path):
    """key.md above an attack file that lives under a cases directory, or None."""
    directory = os.path.dirname(os.path.abspath(attack_path))
    for _ in range(8):
        if f"{os.sep}cases{os.sep}" not in directory + os.sep:
            return None
        candidate = os.path.join(directory, "key.md")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent
    return None


def parse_attack(path):
    """An attack file: verdict, tried inputs, findings, and inputs that held.

    A file with no verdict, no tried input, and no finding does not parse.
    A line `Parse: timeout` (or any Parse: line) does not parse. Broke accepts
    yes or no in any case, with words after it.
    """
    doc = {
        "title": "", "verdict": "", "tried": [], "findings": [], "held": [],
        "held_text": [], "errors": [], "parsed": True,
    }
    section, cur = None, None
    raw_lines = open(path).read().splitlines()
    if any(PARSE_LINE.match(line.strip()) for line in raw_lines) or not "".join(raw_lines).strip():
        doc["parsed"] = False
        doc["errors"].append("unparseable output")
        return doc
    for line in raw_lines:
        if line.startswith("# ") and not line.startswith("## "):
            doc["title"] = line[2:].strip()
            continue
        m = VERDICT.match(line.strip())
        if m and doc["verdict"] == "":
            doc["verdict"] = m.group(1).lower()
            continue
        head = line.strip().lower()
        if head.startswith("## tried"):
            section, cur = "tried", None
            continue
        if head.startswith("## findings"):
            section, cur = "findings", None
            continue
        if head.startswith("## held"):
            section, cur = "held", None
            continue
        if section == "held":
            doc["held_text"].append(line)
        if section in ("tried", "held"):
            m = ITEM.match(line)
            if m:
                cur = {"input": m.group(1).strip(), "observed": "", "broke": ""}
                doc[section].append(cur)
                continue
            if cur is None:
                continue
            m = OBS.match(line)
            if m:
                cur["observed"] = m.group(1).strip()
                continue
            m = BROKE.match(line)
            if m and section == "tried":
                cur["broke"] = m.group(1).lower()
            continue
        if section != "findings":
            continue
        m = FINDING.match(line)
        if m:
            passes = [p.strip() for p in (m.group(3) or "").split(",") if p.strip()]
            cur = {
                "id": m.group(1),
                "where": m.group(2),
                "passes": passes,
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
    if not doc["verdict"] and not doc["tried"] and not doc["findings"]:
        doc["parsed"] = False
        doc["errors"].append("unparseable output")
    return doc


def held_covers(item, held_items, held_text):
    needle = soften(item["input"])
    if not needle:
        return False
    blob = soften("\n".join(held_text))
    if needle in blob:
        return True
    for held in held_items:
        hay = soften(held["input"])
        if hay and (needle in hay or hay in needle):
            return True
    return False


def check_attack(path, key_path=None):
    """Fail strings for one attack file. Empty means it passed."""
    doc = parse_attack(path)
    if not doc["parsed"]:
        return doc["errors"] or ["unparseable output"]
    fails = []
    tried = [t for t in doc["tried"] if t["input"] and t["observed"]]
    if not tried:
        fails.append("zero breaking inputs tried")
    if doc["verdict"] not in ("approve", "needs fixes"):
        fails.append("verdict must be approve or needs fixes")
    for finding in doc["findings"]:
        if not has_location(finding) and not has_repro(finding):
            fails.append(f"{finding['id']} has no location and no repro")
    for item in tried:
        if item["broke"] == "no" and not held_covers(item, doc["held"], doc["held_text"]):
            fails.append("held list omits an input that did not break: " + item["input"])
    if key_path is None:
        key_path = find_key(path)
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
