"""Check an attack review stored as one JSON block.

Usage: python3 check_attack.py <attack.md> [--key <key.md>]
The pass ends with one fenced json block. Prose before it is ignored.
Invalid JSON is an error and is never an approve. An approve needs a
non-empty tried list, every broke flag false, and no findings.
When --key is omitted, a key.md above the file, inside cases, is used.
An empty --key does not turn that lookup off.
"""
import json
import os
import posixpath
import re
import sys

JSON_OPEN = re.compile(r"^(`{3,}|~{3,})[ \t]*json[ \t]*$", re.I)
FENCE_CLOSE = re.compile(r"^(`{3,}|~{3,})[ \t]*$")
MAX_LINE = 1_000_000
WINDOW = 2


def soften(text):
    """Lower case, then drop quotes and backticks so phrasing still matches."""
    text = text.lower().replace("`", "")
    text = re.sub(r"[\"']", "", text)
    return re.sub(r"\s+", " ", text).strip()


def planted_bug(path):
    """True when the key marks a planted bug. Trailing punctuation still counts."""
    for line in open(path, "rb").read().decode("utf-8", "replace").splitlines():
        cleaned = line.strip().lower().replace("*", "").rstrip(" .;:")
        if re.match(r"^planted:\s*yes\b", cleaned):
            return True
    return False


def catch_terms(path):
    """Catch terms from a Catch: line. A term written a/b matches either side."""
    terms = []
    for line in open(path):
        match = re.match(r"^Catch:\s*(.+)$", line.strip())
        if match:
            terms = [part.strip() for part in match.group(1).split("|") if part.strip()]
    return terms


def _bounded(text):
    """An int line, or raise when the digit string is too long to be a line."""
    if len(text) > 7:
        raise ValueError("line out of range")
    value = int(text)
    if value < 0 or value > MAX_LINE:
        raise ValueError("line out of range")
    return value


def _explicit_line(line):
    """A positive line from JSON. 0 and null mean 'use the suffix'. Too big is an error."""
    if line is None or isinstance(line, bool) or not isinstance(line, int):
        return None
    if line > MAX_LINE:
        raise ValueError("line out of range")
    if line <= 0:
        return None
    return line


def norm_span(file, line):
    """(path, start, end). start is None when the finding names no line."""
    if file is None:
        return "", None, None
    text = str(file).strip().replace("\\", "/").replace("`", "")
    text = text.strip("\"' \t")
    if text.lower() in ("", "none", "null"):
        return "", None, None
    text = re.sub(r"^[A-Za-z]:", "", text)
    symbol = re.search(r"::[A-Za-z_][\w.]*\s*$", text)
    if symbol:
        text = text[:symbol.start()]
    embedded = None
    hashed = re.search(r"#L(\d+)(?:-L?(\d+))?\s*$", text, re.I)
    if hashed:
        start = _bounded(hashed.group(1))
        end = _bounded(hashed.group(2)) if hashed.group(2) else start
        embedded = (start, end)
        text = text[:hashed.start()]
    else:
        colon = re.search(r":(\d+)(?::(\d+)|-(\d+))?\s*$", text)
        if colon:
            start = _bounded(colon.group(1))
            end = _bounded(colon.group(3)) if colon.group(3) else start
            embedded = (start, end)
            text = text[:colon.start()]
    if embedded and embedded[1] < embedded[0]:
        embedded = (embedded[1], embedded[0])
    while text.startswith("./"):
        text = text[2:]
    text = posixpath.normpath(text) if text not in ("", ".") else ""
    parts = []
    for part in text.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    if len(parts) > 1 and parts[0] in ("a", "b"):
        parts = parts[1:]
    cut = 0
    for index, part in enumerate(parts):
        if part in ("head", "base"):
            cut = index + 1
        elif part == "cases" and index + 1 < len(parts):
            cut = index + 2
    path = "/".join(parts[cut:])
    if embedded and embedded[0] != embedded[1]:
        return path, embedded[0], embedded[1]
    given = _explicit_line(line)
    if given is not None:
        return path, given, given
    if embedded:
        return path, embedded[0], embedded[1]
    return path, None, None


def norm_location(file, line):
    """(path, first line or None). A range keeps its first line."""
    path, start, _end = norm_span(file, line)
    return path, start


def path_suffix(left, right):
    """True when the shorter path is the trailing components of the longer one."""
    if not left or not right:
        return False
    a, b = left.split("/"), right.split("/")
    if a[-1] != b[-1]:
        return False
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return long[-len(short):] == short


def common_suffix(left, right):
    """Trailing components shared by both paths."""
    a, b = left.split("/"), right.split("/")
    shared = []
    for index in range(1, min(len(a), len(b)) + 1):
        if a[-index] != b[-index]:
            break
        shared.append(a[-index])
    return "/".join(reversed(shared))


def where_span(text):
    """(path, first, last) for file:4 or file:3-4."""
    try:
        path, start, end = norm_span(text, None)
    except ValueError:
        return None
    if not path or start is None:
        return None
    return path, start, end


def unwrap_prefix(line):
    """Drop leading quotes, list markers, and whitespace. The fence can sit behind them."""
    text = line
    while True:
        rest = text.lstrip(" \t")
        if rest.startswith(">"):
            text = rest[1:]
            continue
        marker = re.match(r"^(?:[-*+]|\d+[.)])(?:[ \t]+|$)", rest)
        if marker:
            text = rest[marker.end():]
            continue
        return rest


def json_opens(text):
    """(line index, fence marker) for every fence whose info string is json."""
    found = []
    for index, line in enumerate(text.split("\n")):
        match = JSON_OPEN.match(unwrap_prefix(line))
        if match:
            found.append((index, match.group(1)))
    return found


def one_json_body(text):
    """The single json fence body, a bare object, or (None, error)."""
    opens = json_opens(text)
    if len(opens) > 1:
        return None, "more than one json block"
    if not opens:
        bare = text.strip()
        if bare.startswith("{") or bare.startswith(">"):
            bare = "\n".join(unwrap_prefix(line) for line in text.split("\n")).strip()
        if bare.startswith("{"):
            return bare, None
        return None, "missing json block"
    start, marker = opens[0]
    lines = text.split("\n")
    char, width = marker[0], len(marker)
    for index in range(start + 1, len(lines)):
        close = FENCE_CLOSE.match(unwrap_prefix(lines[index]))
        if close and close.group(1)[0] == char and len(close.group(1)) >= width:
            body = "\n".join(unwrap_prefix(line) for line in lines[start + 1:index])
            return body, None
    return None, "unclosed json block"


def finding_span(finding):
    """(path, start, end). A stored line_start/line_end keeps a range through the merge."""
    raw_start = finding.get("line_start")
    raw_end = finding.get("line_end")
    has_start = isinstance(raw_start, int) and not isinstance(raw_start, bool)
    has_end = isinstance(raw_end, int) and not isinstance(raw_end, bool)
    if not has_start and not has_end:
        return norm_span(finding.get("file"), finding.get("line"))
    if (has_start and raw_start > MAX_LINE) or (has_end and raw_end > MAX_LINE):
        raise ValueError("line out of range")
    path, _, _ = norm_span(finding.get("file"), None)
    start = raw_start if has_start else raw_end
    end = raw_end if has_end else raw_start
    if start is None or start <= 0:
        return path, None, None
    if end is None or end <= 0:
        end = start
    if end < start:
        start, end = end, start
    return path, start, end


def _pairs(pairs):
    """object_pairs_hook. A repeated key is an error, not a silent overwrite."""
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError("duplicate key")
        seen[key] = value
    return seen


def _line_ok(value):
    if value is None:
        return True
    if isinstance(value, bool) or not isinstance(value, int):
        return False
    if value < 0 or value > MAX_LINE:
        return False
    return True


def _coerce(data):
    """Fold verdict case and accept a numeric line written as a string."""
    if not isinstance(data, dict):
        return
    verdict = data.get("verdict")
    if isinstance(verdict, str):
        folded = verdict.strip().lower()
        if folded in ("approve", "needs fixes"):
            data["verdict"] = folded
    findings = data.get("findings")
    if not isinstance(findings, list):
        return
    for item in findings:
        if not isinstance(item, dict):
            continue
        line = item.get("line")
        if isinstance(line, str) and re.fullmatch(r"\d+", line.strip()):
            number = int(line.strip())
            if 0 <= number <= MAX_LINE:
                item["line"] = number


def _schema_error(data):
    if not isinstance(data, dict) or not {"verdict", "tried", "findings"} <= set(data):
        return "schema keys"
    if data["verdict"] not in ("approve", "needs fixes"):
        return "verdict value"
    if not isinstance(data["tried"], list) or not isinstance(data["findings"], list):
        return "schema types"
    for item in data["tried"]:
        if not isinstance(item, dict) or not {"input", "broke", "observed"} <= set(item):
            return "tried item"
        if not isinstance(item["input"], str) or not isinstance(item["observed"], str):
            return "tried types"
        if not isinstance(item["broke"], bool):
            return "broke type"
    for item in data["findings"]:
        if not isinstance(item, dict) or not {"file", "line", "claim", "repro"} <= set(item):
            return "finding keys"
        if not isinstance(item["file"], str) or not isinstance(item["claim"], str) or not isinstance(item["repro"], str):
            return "finding types"
        if not _line_ok(item["line"]):
            return "line type"
    return None


def effective_verdict(data):
    """Approve only when the JSON says so, something was tried, nothing broke, and there is no finding."""
    broke = any(item["broke"] for item in data["tried"])
    if data["findings"] or broke:
        return "needs fixes"
    if data["verdict"] == "approve" and data["tried"]:
        return "approve"
    return "needs fixes"


def parse_attack(path):
    """The JSON pass, or an error document. Prose and markdown headings are ignored."""
    doc = {
        "parsed": False, "errors": [], "verdict": "", "stated": "",
        "tried": [], "findings": [], "title": "",
    }
    try:
        text = open(path, "rb").read().decode("utf-8")
    except (FileNotFoundError, IsADirectoryError, OSError):
        doc["errors"].append("missing pass")
        return doc
    except UnicodeDecodeError:
        doc["errors"].append("file is not UTF-8")
        return doc
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        doc["errors"].append("unparseable output")
        return doc
    raw, problem = one_json_body(text)
    if problem or raw is None:
        doc["errors"].append(problem or "missing json block")
        return doc
    try:
        data = json.loads(raw, object_pairs_hook=_pairs)
        _coerce(data)
        problem = _schema_error(data)
    except (json.JSONDecodeError, ValueError, OverflowError):
        doc["errors"].append("invalid json")
        return doc
    if not isinstance(data, dict):
        doc["errors"].append("invalid json")
        return doc
    if problem:
        doc["errors"].append(problem)
        return doc
    doc["parsed"] = True
    doc["stated"] = data["verdict"]
    doc["verdict"] = effective_verdict(data)
    doc["tried"] = data["tried"]
    doc["findings"] = data["findings"]
    return doc


def _case_key(directory):
    """cases/<name>/key.md walking up from a directory, or None."""
    while True:
        parent = os.path.dirname(directory)
        if os.path.basename(parent) == "cases":
            candidate = os.path.join(directory, "key.md")
            return candidate if os.path.isfile(candidate) else None
        if parent == directory:
            return None
        directory = parent


def find_key(attack_path):
    """cases/<name>/key.md. The symlink's own directory and its target both count."""
    seen = []
    for path in (attack_path,):
        seen.append(os.path.dirname(os.path.abspath(path)))
    try:
        seen.append(os.path.dirname(os.path.realpath(attack_path)))
    except OSError:
        pass
    for directory in seen:
        found = _case_key(directory)
        if found:
            return found
    return None


def check_attack(path, key_path=None):
    """Fail strings for one attack file. Empty means it passed."""
    doc = parse_attack(path)
    if not doc["parsed"]:
        return doc["errors"] or ["unparseable output"]
    fails = []
    if doc["stated"] == "approve" and doc["verdict"] != "approve":
        fails.append("not a valid approve")
    if doc["verdict"] == "approve" and (doc["findings"] or any(item["broke"] for item in doc["tried"])):
        fails.append("approve contradicts a break")
    case_key = find_key(path)
    if case_key:
        key_path = case_key
    elif not key_path:
        key_path = None
    if key_path and planted_bug(key_path) and doc["verdict"] == "approve":
        fails.append("approve on a case with a planted bug")
    return fails


def _main(argv):
    from cli import usage_or_exit
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    args, key = [], None
    index = 1
    while index < len(argv):
        if argv[index] == "--key":
            if index + 1 >= len(argv):
                print((__doc__ or "").strip(), file=sys.stderr)
                return 2
            value = argv[index + 1].strip()
            if value:
                key = value
            index += 2
            continue
        if argv[index].startswith("--"):
            print((__doc__ or "").strip(), file=sys.stderr)
            return 2
        args.append(argv[index])
        index += 1
    if len(args) != 1:
        usage_or_exit(__doc__, ["check_attack.py"], 1)
    fails = check_attack(args[0], key)
    print(f"{'FAIL' if fails else 'PASS'} attack: {os.path.basename(args[0])}")
    for item in fails:
        print(f"  {item}")
    return 1 if fails else 0


def main(argv):
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
