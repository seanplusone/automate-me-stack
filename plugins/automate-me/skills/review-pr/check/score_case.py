"""Scores a review against a case key.

Usage: python3 score_case.py <cases/<name>/key.md> <review.md>
Exits 1 if any key finding is missed.

A key with a line `Planted: yes` scores an attack file. A finding matches when
its file matches the key file and its line overlaps the key span, plus or
minus 2. A null line still needs that file, plus a repro. The judge then
decides, and only those findings are sent. With no CLI the result is weak.
It prints SKIP for meaning, checks the location only, and exits 2. Exit 2 is
not a judged catch. Any other key scores a drafts file, below.

A key row is `| <id> | <pr> | <path prefix> | <line or -> | <finding> | <min sites or -> | <proof> |`.
A finding is found when the drafts carry a comment in that PR on a path that starts with the
prefix and, when the row names a line, within LINE_WINDOW lines of it. A row whose path is `PR`
wants a PR-level comment, one with `PR` in place of `<path>:<line>`. The window allows for a
comment anchored on the nearest changed line. A row with a minimum also needs that comment's
`Sites:` count to reach it.
An optional line `Terms: K1 | admin | owner` outside the table also requires one on-target comment
to contain every listed term (case-insensitive, posted comment text only). A term written `a/b`
matches either word.
Without it this checks placement and counts only; wording is still scored by a person.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_attack import catch_terms, finding_span, parse_attack, path_suffix, planted_bug, where_span  # noqa: E402
from check_drafts import parse  # noqa: E402

ROW = re.compile(r"^\| (K\d+) \| (\S+#\d+) \| `?([^|`]+?)`? \| (\d+|-) \| [^|]+ \| (\d+|-) \| [^|]* \|$")
LINE_WINDOW = 3


def on_target(anchor, prefix, line):
    if anchor == "PR" or prefix == "PR":
        return anchor == prefix
    path, at = anchor.rsplit(":", 1)
    return path.startswith(prefix) and (line == "-" or abs(int(at) - int(line)) <= LINE_WINDOW)


def key_rows(path):
    return [ROW.match(line.strip()).groups() for line in open(path) if ROW.match(line.strip())]


def key_terms(path):
    terms = {}
    for line in open(path):
        m = re.match(r"^Terms:\s*(K\d+)\s*\|(.+)$", line.strip())
        if m:
            terms[m.group(1)] = [t.strip().lower() for t in m.group(2).split("|") if t.strip()]
    return terms


def missing_terms(hits, terms):
    """Terms absent from the on-target comment that lacks the fewest."""
    def absent(term, text):
        return not any(alt in text for alt in term.split("/"))
    return min(([t for t in terms if absent(t, " ".join(f["comment"]).lower())] for f in hits), key=len)


def key_where(path):
    for line in open(path):
        match = re.match(r"^Where:\s*`?(.*?)`?\s*$", line.strip())
        if match and match.group(1):
            return match.group(1)
    return ""


def matches(finding, want):
    """The file matches, and the line overlaps the key span. A null line needs a repro."""
    try:
        path, start, end = finding_span(finding)
    except ValueError:
        return False
    if not path:
        return False
    repro = bool((finding.get("repro") or "").strip())
    if not want:
        return start is not None or repro
    span = where_span(want)
    if not span or not path_suffix(path, span[0]):
        return False
    if start is None:
        return repro
    return start <= span[2] + 2 and end >= span[1] - 2


def _symbol_only(finding):
    """A file::symbol suffix names the file and leaves the line to the judge."""
    if "::" not in str(finding.get("file") or ""):
        return False
    try:
        _path, start, _end = finding_span(finding)
    except ValueError:
        return False
    return start is None


def _for_judge(finding, want):
    if not _symbol_only(finding):
        return False
    try:
        path, _start, _end = finding_span(finding)
    except ValueError:
        return False
    if not path:
        return False
    if not want:
        return True
    span = where_span(want)
    return bool(span and path_suffix(path, span[0]))


def _broke_rows(doc):
    """A break with no finding is evidence for the judge, not a location hit."""
    rows = []
    for item in doc.get("tried") or []:
        if item.get("broke") is not True:
            continue
        rows.append({
            "file": "",
            "line": None,
            "claim": item.get("observed") or "",
            "repro": item.get("input") or "",
            "observed": item.get("observed") or "",
        })
    return rows


def repro_mentions(finding, want):
    """An empty file can still name the key file in its repro."""
    try:
        path, _start, _end = finding_span(finding)
    except ValueError:
        return False
    repro = (finding.get("repro") or "").strip()
    if path or not repro:
        return False
    if not want:
        return True
    span = where_span(want)
    if not span:
        return False
    name = span[0].split("/")[-1].lower()
    return name in repro.lower()


def score_planted(key_path, attack_path, environ=None, runner=None):
    """The judge decides on matching findings. With no CLI, only the location is checked."""
    terms = catch_terms(key_path)
    if not terms:
        print(f"FAIL no Catch terms in {key_path}")
        return 1
    doc = parse_attack(attack_path)
    if not doc["parsed"]:
        print("FAIL missed planted bug")
        return 1
    want = key_where(key_path)
    located = [
        finding for finding in doc["findings"]
        if matches(finding, want) and not _symbol_only(finding)
    ]
    symbols = [finding for finding in doc["findings"] if _for_judge(finding, want)]
    mentioned = [finding for finding in doc["findings"] if repro_mentions(finding, want)]
    broke_rows = _broke_rows(doc) if not doc["findings"] else []
    usable = located + symbols + mentioned + broke_rows
    if not usable:
        print("FAIL missed planted bug")
        return 1
    from judge_case import find_cli, judge  # noqa: E402
    if runner is None and find_cli(environ) is None:
        if not located:
            print("FAIL missed planted bug")
            return 1
        print("SKIP no agent CLI on PATH")
        print("SKIP meaning")
        print("WEAK location only")
        return 2
    judged = judge(key_path, attack_path, environ=environ, runner=runner, findings=usable)
    if judged == 0:
        return 0
    if judged == 2:
        return 2
    print("FAIL missed planted bug")
    return 1


def score(key_path, drafts_path, environ=None, runner=None):
    if planted_bug(key_path):
        return score_planted(key_path, drafts_path, environ=environ, runner=runner)
    prs, _ = parse(drafts_path)
    rows = key_rows(key_path)
    terms = key_terms(key_path)
    if not rows:
        print(f"FAIL no scorable rows in {key_path}")
        return 1
    missed = 0
    for kid, pr, prefix, line, min_sites in rows:
        hits = [f for p in prs if p["pr"].endswith("/" + pr) or p["pr"] == pr
                for f in p["findings"] if f["match"] and on_target(f["match"].group(2), prefix, line)]
        best = max((int(s.split("|")[0]) for f in hits for s in f["sites"]), default=0)
        if not hits:
            result = "MISSED no comment on " + prefix + ("" if line == "-" else f" near line {line}")
        elif terms.get(kid) and missing_terms(hits, terms[kid]):
            result = "MISSED comment on the line does not name: " + ", ".join(missing_terms(hits, terms[kid]))
        elif min_sites != "-" and best < int(min_sites):
            result = f"MISSED Sites {best or 'absent'}, key needs at least {min_sites}"
        else:
            result = "found"
        missed += result != "found"
        print(f"{kid} {pr} {result}")
    print(f"{'FAIL' if missed else 'PASS'} {len(rows) - missed}/{len(rows)} key findings")
    return 1 if missed else 0


if __name__ == "__main__":
    try:
        from cli import usage_or_exit
        usage_or_exit(__doc__, sys.argv, 2)
        sys.exit(score(sys.argv[1], sys.argv[2]))
    except SystemExit:
        raise
    except Exception:
        print((__doc__ or "").strip(), file=sys.stderr)
        sys.exit(2)
