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
REPRO = re.compile(r"^Repro:\s*(.*)$", re.I)
HEAD_ID = re.compile(r"^(?P<id>[A-Za-z0-9_-]+)\s*[:|]\s*(?P<rest>.+)$")
PASSES = re.compile(r"\(?\s*passes:\s*([^)|]+)", re.I)
LINE_WORD = re.compile(r"(\S+)\s+line\s+(\d+)\b", re.I)
WHERE_TOKEN = re.compile(r"(\S+:\d+)\b")
WHERE = re.compile(r"^\S+:\d+$")
PARSE_LINE = re.compile(r"^Parse:\s*\S", re.I)


def norm(text):
    return re.sub(r"\s+", " ", text.strip())


def soften(text):
    """Lower case, then drop quotes and backticks so phrasing still matches."""
    text = text.lower().replace("`", "")
    text = re.sub(r"[\"']", "", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_marks(line):
    """Drop bold, backticks, and a leading heading marker."""
    text = line.strip().replace("**", "").replace("__", "").replace("`", "")
    return re.sub(r"^#+\s*", "", text).strip()


def planted_bug(path):
    """True when the key marks a case that hides a bug the review must not approve.

    `Planted: yes.` counts. Trailing punctuation does not hide it.
    """
    for line in open(path, "rb").read().decode("utf-8", "replace").splitlines():
        cleaned = strip_marks(line).lower().rstrip(" .;:")
        if re.match(r"^planted:\s*yes\b", cleaned):
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


def heading_depth(line):
    """How many leading # the line has, after a wrapping bold marker is removed."""
    probe = line.strip().replace("**", "").replace("__", "")
    depth = 0
    for char in probe:
        if char == "#":
            depth += 1
        else:
            break
    return depth


def parse_finding_heading(line):
    """A real finding heading, or None.

    A finding heading has at least three hashes: ### or ####, not a ## section.
    Also accepts a colon or a pipe, bold markers, `(passes: name)`, and
    `cap.py line 3`. Lines longer than 500 characters are not headings.
    """
    raw = line.strip()
    if not raw or len(raw) > 500 or heading_depth(raw) < 3:
        return None
    looks = True
    cleaned = strip_marks(raw)
    if not looks and not cleaned[:1].isalnum():
        return None
    passes = []
    found = PASSES.search(cleaned)
    if found:
        passes = [part.strip(" )") for part in found.group(1).split(",") if part.strip(" )")]
        cleaned = cleaned[:found.start()].strip(" |:")
    where, fid = None, None
    match = HEAD_ID.match(cleaned)
    if match:
        fid = match.group("id")
        rest = match.group("rest").strip()
        token = WHERE_TOKEN.match(rest)
        words = LINE_WORD.match(rest)
        if token:
            where = token.group(1)
        elif words:
            where = f"{words.group(1)}:{words.group(2)}"
        elif rest == "none" or rest.startswith("none"):
            where = "none"
    if where is None and looks:
        words = LINE_WORD.search(cleaned)
        token = WHERE_TOKEN.search(cleaned)
        if words:
            where = f"{words.group(1)}:{words.group(2)}"
            fid = fid or "F"
        elif token:
            where = token.group(1)
            fid = fid or "F"
    if not looks or not where:
        return None
    return {"id": fid or "F", "where": where, "passes": passes}


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


def outside_fences(lines):
    """Lines that are not inside a fenced code block."""
    kept, fenced = [], False
    for line in lines:
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return kept


def finding_like(line):
    """True when the line names a file and line, a 'line N', or an F<digit> heading.

    The scan is bounded so a huge line cannot blow up the matcher.
    """
    if len(line) > 500:
        line = line[:500]
    if re.search(r"(?<![A-Za-z0-9])F\d+\b", line):
        return True
    if re.search(r"(?i)(?<![A-Za-z0-9])line\s+\d+\b", line):
        return True
    if re.search(r"(?<![A-Za-z0-9_])[A-Za-z0-9_./\\-]{1,180}:\d+\b", line):
        return True
    return False


def classify(doc):
    """approve only for one explicit approve, tried inputs that all held, and no finding.

    Anything else that parsed is needs fixes. An unparsed pass is error.
    """
    if not doc.get("parsed", False):
        return "error"
    verdicts = doc.get("verdicts") or []
    tried = [item for item in doc["tried"] if item["input"] and item.get("observed")]
    clean = (
        verdicts == ["approve"]
        and tried
        and all(item.get("broke") == "no" for item in tried)
        and not doc.get("findingish")
        and not doc.get("findings")
    )
    return "approve" if clean else "needs fixes"


def parse_attack(path):
    """An attack file: verdict, tried inputs, findings, and inputs that held.

    Verdict and Broke lines may be bold. Section names may use ## or ###.
    Lines inside ``` fences are examples, not the review. A `Parse:` line,
    an empty file, or a non-UTF-8 file does not parse. Broke accepts yes or
    no in any case, with words after it.
    """
    doc = {
        "title": "", "verdict": "", "verdicts": [], "tried": [], "findings": [],
        "held": [], "held_text": [], "errors": [], "parsed": True, "findingish": False,
    }
    try:
        raw_lines = open(path, "rb").read().decode("utf-8").splitlines()
    except UnicodeDecodeError:
        doc["parsed"] = False
        doc["errors"].append("file is not UTF-8")
        return doc
    if any(PARSE_LINE.match(strip_marks(line)) for line in raw_lines) or not "".join(raw_lines).strip():
        doc["parsed"] = False
        doc["errors"].append("unparseable output")
        return doc
    visible = outside_fences(raw_lines)
    doc["findingish"] = any(finding_like(line) for line in visible)
    section, cur, fenced = None, None, False
    for line in raw_lines:
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("# ") and not line.startswith("##"):
            doc["title"] = strip_marks(line)
            continue
        cleaned = strip_marks(line)
        low = cleaned.lower()
        if re.match(r"^verdict:\s*approve\b", low):
            doc["verdicts"].append("approve")
            continue
        if re.match(r"^verdict:\s*needs fixes\b", low):
            doc["verdicts"].append("needs fixes")
            continue
        if heading_depth(line) >= 2 and low.startswith("tried"):
            section, cur = "tried", None
            continue
        if heading_depth(line) >= 2 and low.startswith("findings"):
            section, cur = "findings", None
            continue
        if heading_depth(line) >= 2 and low.startswith("held"):
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
            broke = re.match(r"^broke:\s*(yes|no)\b", low)
            if broke and section == "tried":
                cur["broke"] = broke.group(1).lower()
            continue
        if section != "findings":
            continue
        heading = parse_finding_heading(line)
        if heading:
            cur = {
                "id": heading["id"],
                "where": heading["where"],
                "passes": heading["passes"],
                "claim": [],
                "repro": "",
                "observed": "",
                "raw": False,
            }
            doc["findings"].append(cur)
            continue
        m = REPRO.match(line)
        if m and cur is not None:
            cur["repro"] = m.group(1).strip()
            continue
        m = OBS.match(line)
        if m and cur is not None:
            cur["observed"] = m.group(1).strip()
            continue
        if line.strip():
            if cur is None:
                cur = {
                    "id": "raw", "where": "none", "passes": [], "claim": [],
                    "repro": "", "observed": "", "raw": True,
                }
                doc["findings"].append(cur)
            cur["claim"].append(line.strip())
    if "needs fixes" in doc["verdicts"]:
        doc["verdict"] = "needs fixes"
    elif doc["verdicts"] == ["approve"]:
        doc["verdict"] = "approve"
    else:
        doc["verdict"] = ""
    if not doc["verdict"] and not doc["tried"] and not doc["findings"] and not doc["findingish"]:
        doc["parsed"] = False
        doc["errors"].append("unparseable output")
    return doc


def held_covers(item, held_items, held_text):
    """True when Held still contains the input, quotes and backticks included."""
    raw = item["input"].strip()
    if raw == "":
        return False
    blob = "\n".join(held_text)
    if raw in blob:
        return True
    for held in held_items:
        hay = held["input"].strip()
        if hay and (raw == hay or raw in hay or hay in raw):
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
    if doc["verdict"] == "approve" and classify(doc) != "approve":
        fails.append("not a valid approve")
    located = any(has_location(finding) for finding in doc["findings"])
    broke_yes = any(item["broke"] == "yes" for item in tried)
    if doc["verdict"] == "approve" and (located or broke_yes or doc.get("findingish")):
        fails.append("approve contradicts a break")
    if not key_path:
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
            key = argv[i + 1].strip() or None
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
