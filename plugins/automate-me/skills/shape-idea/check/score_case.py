"""Scores a shape-idea decisions.md against a case key.

Usage: python3 check/score_case.py <cases/<name>/key.md> <decisions.md>

Key lines, one item each, outside code blocks. Terms are separated by ` | `. A term written
`a/b` matches either side. Matching ignores case. A term matches at the start of a word, so
`pet` matches `pets` but not `carpet`. A term of 3 letters or fewer must be the whole word,
or that word plus s. A term that ends in a digit must end the number, so `10` is not `100`.
A term of several words matches as a phrase. The same rules as outcome's scorer.

  Decided: <slot or id> | <term> ...
  Open: <slot or id> | <term> ...
  Parked: <slot or id> | <term> ...

When the first field is goal, done, output, verify, or constraints, every term must sit on
that slot's line in the section. Otherwise every term must sit on one line in the section
that is not one of those slots. Keywords on a different line do not count.
A section whose only item is `none` is empty. Lines inside code blocks are skipped.

Prints one line per key item (`found` or `MISSED`), then `PASS n/m` or `FAIL n/m`.
Exit 0 when every item matched. Exit 1 on any miss, or when the key has no scorable lines.
Exit 2 on a usage error.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_decisions import SLOTS, canon, parse, real_items, slot_of  # noqa: E402

KEY_LINE = re.compile(r"^(Decided|Open|Parked):\s*(.+)$", re.I)


def read_key(path):
    items, fenced = [], False
    for line in open(path):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        match = KEY_LINE.match(line.strip())
        if match and not fenced:
            kind = canon(match.group(1))
            parts = [p.strip() for p in match.group(2).split(" | ") if p.strip()]
            items.append((kind, parts))
    return items


def term_pattern(alt):
    """Word-start match. See the module docstring. Copied from outcome's score_case."""
    body = r"\s+".join(re.escape(w) for w in alt.split())
    left = r"(?<!\w)" if alt[0].isalnum() or alt[0] == "_" else ""
    right = r"(?!\d)" if alt[-1].isdigit() else ""
    if len(alt) <= 3 and alt.isalpha():
        right = r"s?(?!\w)"
    return left + body + right


def term_in(term, text):
    return any(re.search(term_pattern(alt), text, re.I) for alt in term.split("/") if alt.strip())


def missing(terms, text):
    return [t for t in terms if not term_in(t, text)]


def named(parts):
    if len(parts) == 1:
        return parts[0], parts
    return parts[0], parts[1:]


def score(key_path, decisions_path):
    sections, _, _, _ = parse(open(decisions_path).read())
    items = read_key(key_path)
    if not items:
        print(f"FAIL no scorable lines in {key_path}")
        return 1
    misses = 0
    for kind, parts in items:
        ident, terms = named(parts)
        body = real_items(sections.get(kind, []))
        if ident.lower() in SLOTS:
            body = [item for item in body if slot_of(item) == ident.lower()]
        else:
            body = [item for item in body if slot_of(item) is None]
        best = min((missing(terms, item) for item in body), key=len, default=list(terms))
        result = "found" if not best else f"MISSED no {kind.lower()} item names: " + ", ".join(best)
        misses += result.startswith("MISSED")
        print(f"{kind.lower()} {ident}: {result}")
    print(f"{'FAIL' if misses else 'PASS'} {len(items) - misses}/{len(items)} key items")
    return 1 if misses else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(score(sys.argv[1], sys.argv[2]))
