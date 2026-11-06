"""Scores an outcome brief against a case key.

Usage: python3 check/score_case.py <cases/<name>/key.md> <brief.md>

Key lines, one item each, outside code blocks. Terms are separated by ` | `; a term written `a/b`
matches either side. Matching ignores case.

  Fact: <term> | <term> ...       each term appears in the brief exactly as written. A term that
                                  starts or ends with a letter or digit must not run into another
                                  one, so `10` does not match `100` and `2600` does not match `2,600`.
  Slot: <Label> | <term> ...      the slot's text holds every term.
  Unknown: <id> | <term> ...      one unknown marker (`unknown: ...?`) or one numbered question holds
                                  every term. The gap was asked, not guessed.
  Forbidden: <id> | <regex>       the regex matches nowhere in the brief once every sentence that ends
                                  in `?` is removed. A match means the brief invented a fact.
  Parking: <id> | <term> ...      the Parking lot slot holds every term.

Prints one line per key item (`found`, `clear` for a forbidden guess not made, or `MISSED`), then `PASS n/m` or `FAIL n/m`. Exits 1 on any miss.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import UNKNOWN_START, canon, parse  # noqa: E402

KEY_LINE = re.compile(r"^(Fact|Slot|Unknown|Forbidden|Parking):\s*(.+)$")


def read_key(path):
    items, fenced = [], False
    for line in open(path):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        m = KEY_LINE.match(line.strip())
        if m and not fenced:
            items.append((m.group(1), [p.strip() for p in m.group(2).split(" | ") if p.strip()]))
    return items


def fact_found(term, text):
    for alt in term.split("/"):
        left = r"(?<![\w,])" if alt[0].isalnum() else ""
        right = r"(?![\w]|,\d)" if alt[-1].isalnum() else ""
        if re.search(left + re.escape(alt) + right, text, re.I):
            return True
    return False


def term_in(term, text):
    return any(alt.lower() in text.lower() for alt in term.split("/"))


def missing(terms, text):
    return [t for t in terms if not term_in(t, text)]


def without_questions(text):
    return re.sub(r"[^.?!\n]*\?", " ", text)


def score(key_path, brief_path):
    text = open(brief_path).read()
    slots, questions, _ = parse(text)
    unknown_items = [i for items in slots.values() for i in items if UNKNOWN_START.match(i)] + questions
    items = read_key(key_path)
    if not items:
        print(f"FAIL no scorable lines in {key_path}")
        return 1
    misses = 0
    for kind, parts in items:
        if kind == "Fact":
            lost = [t for t in parts if not fact_found(t, text)]
            name, result = "facts " + ", ".join(parts), "MISSED not verbatim: " + ", ".join(lost) if lost else "found"
        elif kind == "Slot":
            label = parts[0]
            try:
                body = " ".join(slots.get(canon(label), []))
            except StopIteration:
                body = ""
            lost = missing(parts[1:], body)
            name, result = f"slot {label}", ("MISSED slot does not name: " + ", ".join(lost)) if lost else "found"
        elif kind == "Unknown":
            best = min((missing(parts[1:], i) for i in unknown_items), key=len, default=parts[1:])
            name = f"unknown {parts[0]}"
            result = ("MISSED no unknown or question names: " + ", ".join(best)) if best else "found"
        elif kind == "Forbidden":
            m = re.search(parts[1], without_questions(text), re.I)
            name = f"forbidden {parts[0]}"
            result = f"MISSED guessed a fact: {m.group(0)!r}" if m else "clear"
        else:
            lost = missing(parts[1:], " ".join(slots.get("Parking lot", [])))
            name = f"parking {parts[0]}"
            result = ("MISSED parking lot does not name: " + ", ".join(lost)) if lost else "found"
        misses += result.startswith("MISSED")
        print(f"{name}: {result}")
    print(f"{'FAIL' if misses else 'PASS'} {len(items) - misses}/{len(items)} key items")
    return 1 if misses else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(score(sys.argv[1], sys.argv[2]))
