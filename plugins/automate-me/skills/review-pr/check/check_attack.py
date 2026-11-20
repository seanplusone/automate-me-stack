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

PARSE_LINE = re.compile(r"^Parse:\s*\S", re.I)
JSON_OPEN = re.compile(r"^(`{3,})json\s*$", re.I)
FENCE_CLOSE = re.compile(r"^(`{3,})\s*$")


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


def norm_location(file, line):
    """(path, line or None). Strips ./, .., absolute prefixes, :col and #L."""
    if file is None:
        return "", None
    text = str(file).strip().replace("\\", "/")
    if text.lower() in ("", "none", "null"):
        return "", None
    embedded = None
    hash_line = re.search(r"#L(\d+)\s*$", text, re.I)
    if hash_line:
        embedded = int(hash_line.group(1))
        text = text[:hash_line.start()]
    colon = re.search(r":(\d+)(?::\d+)?$", text)
    if colon:
        if embedded is None:
            embedded = int(colon.group(1))
        text = text[:colon.start()]
    while text.startswith("./"):
        text = text[2:]
    if text.startswith("/"):
        text = posixpath.normpath(text)
    else:
        text = posixpath.normpath(text) if text else ""
    if text in ("", "."):
        return "", line if isinstance(line, int) and not isinstance(line, bool) else embedded
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if text.startswith("/") and "cases" not in parts and "head" not in parts and "base" not in parts:
        parts = parts[-1:]
    if len(parts) >= 3 and parts[0] == "cases":
        parts = parts[2:]
    last = None
    for index, part in enumerate(parts):
        if part in ("head", "base"):
            last = index
    if last is not None:
        parts = parts[last + 1:]
    path = "/".join(parts)
    if isinstance(line, int) and not isinstance(line, bool):
        use = line
    else:
        use = embedded
    return path, use


def where_span(text):
    """(path, first, last) for file:4 or file:3-4."""
    match = re.match(r"^(.*?):(\d+)(?:-(\d+))?$", text.strip().strip("`"))
    if not match:
        return None
    start, end = int(match.group(2)), int(match.group(3) or match.group(2))
    if end < start:
        start, end = end, start
    path, _line = norm_location(match.group(1), start)
    if not path:
        return None
    return path, start, end


def last_json_block(text):
    """Body of the last ```json fence, or None. A 4-backtick wrapper does not hide it."""
    lines = text.splitlines()
    opens = []
    for index, line in enumerate(lines):
        match = JSON_OPEN.match(line.strip())
        if match:
            opens.append((index, len(match.group(1))))
    if not opens:
        return None
    start, width = opens[-1]
    for index in range(start + 1, len(lines)):
        close = FENCE_CLOSE.match(lines[index].strip())
        if close and len(close.group(1)) >= width:
            return "\n".join(lines[start + 1:index])
    return None


def _schema_error(data):
    if not isinstance(data, dict) or set(data) != {"verdict", "tried", "findings"}:
        return "schema keys"
    if data["verdict"] not in ("approve", "needs fixes"):
        return "verdict value"
    if not isinstance(data["tried"], list) or not isinstance(data["findings"], list):
        return "schema types"
    for item in data["tried"]:
        if not isinstance(item, dict) or set(item) != {"input", "broke", "observed"}:
            return "tried item"
        if not isinstance(item["input"], str) or not isinstance(item["observed"], str):
            return "tried types"
        if not isinstance(item["broke"], bool):
            return "broke type"
    for item in data["findings"]:
        if not isinstance(item, dict) or set(item) != {"file", "line", "claim", "repro"}:
            return "finding keys"
        if not isinstance(item["file"], str) or not isinstance(item["claim"], str) or not isinstance(item["repro"], str):
            return "finding types"
        if isinstance(item["line"], bool) or (item["line"] is not None and not isinstance(item["line"], int)):
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
    except UnicodeDecodeError:
        doc["errors"].append("file is not UTF-8")
        return doc
    if not text.strip() or any(PARSE_LINE.match(line.strip()) for line in text.splitlines()):
        doc["errors"].append("unparseable output")
        return doc
    raw = last_json_block(text)
    if raw is None:
        doc["errors"].append("missing json block")
        return doc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        doc["errors"].append("invalid json")
        return doc
    problem = _schema_error(data)
    if problem:
        doc["errors"].append(problem)
        return doc
    doc["parsed"] = True
    doc["stated"] = data["verdict"]
    doc["verdict"] = effective_verdict(data)
    doc["tried"] = data["tried"]
    doc["findings"] = data["findings"]
    return doc


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
    if not key_path:
        key_path = find_key(path)
    if key_path and planted_bug(key_path) and doc["verdict"] == "approve":
        fails.append("approve on a case with a planted bug")
    return fails


def main(argv):
    from cli import usage_or_exit
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        print((__doc__ or "").strip())
        return 0
    args, key = [], None
    index = 1
    while index < len(argv):
        if argv[index] == "--key":
            if index + 1 >= len(argv):
                usage_or_exit(__doc__, ["check_attack.py"], 1)
            key = argv[index + 1].strip() or None
            index += 2
            continue
        args.append(argv[index])
        index += 1
    if len(args) != 1:
        usage_or_exit(__doc__, ["check_attack.py"], 1)
    fails = check_attack(args[0], key)
    print(f"{'FAIL' if fails else 'PASS'} attack: {os.path.basename(args[0])}")
    for item in fails:
        print(f"  {item}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
