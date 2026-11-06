"""Checks the shape of a brief written by the outcome skill.

Usage: python3 check/check_brief.py <brief.md>

A slot is a top-level line `- <Label>: <value>`. A note in brackets after the label is allowed, as in
`- Taste (flag, don't filter):`. Indented `  - <item>` lines under it are more items of the same slot.
The labels are fixed (see REQUIRED and OPTIONAL). Questions go in a block headed
`## Questions`, as numbered lines `1. <question>?`.

Fails when:
- a required slot is missing, or any slot label appears more than once;
- a slot has no value and no items;
- Plan first does not start with `yes` or `none needed`;
- an `investigate:` or `out of scope:` item sits outside Must-haves, or a `how:` item outside Skills;
- a slot that holds `unknown:` also offers a default;
- an item that starts with `unknown` is not `unknown: <question>?` (a note may follow the question);
- the Unknowns slot is not `none` and holds an item that is not an unknown marker;
- the Unknowns slot says `none` while another slot holds an unknown marker;
- there are unknowns but no Questions block, or the block has more than 3 numbered questions,
  or a numbered question has no question mark;
- an item is only trap adjectives (modern, clean, good, better, correct, valid, nice), with no
  visible signal named.
Prints a PASS or FAIL line per check and exits 1 on any FAIL.
"""
import re
import sys

REQUIRED = ["Plan first", "Goal", "Decision", "Context", "Must-haves", "Taste", "Output", "Verify", "If stuck",
            "Skills", "Parking lot", "Unknowns"]
OPTIONAL = ["Kind"]
LABELS = REQUIRED + OPTIONAL
SLOT = re.compile(r"^- (" + "|".join(map(re.escape, LABELS)) + r")(?:\s*\([^)]*\))?:(.*)$", re.I)
SUB = re.compile(r"^\s+[-*]\s+(.*)$")
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
UNKNOWN_START = re.compile(r"^unknown\b", re.I)
UNKNOWN_OK = re.compile(r"^unknown:\s*[^?\s][^?]*\?", re.I)
TRAP = {"modern", "clean", "good", "better", "correct", "valid", "nice"}
FILLER = {"a", "an", "the", "it", "its", "is", "be", "should", "must", "make", "made", "very", "really", "and",
          "or", "more", "look", "looks", "feel", "feels", "pretty", "just", "kind", "of", "enough", "to"}
MAX_QUESTIONS = 3
PLAN_OK = re.compile(r"^(yes\b|none needed\b)", re.I)
TAGS = {"investigate": ["Must-haves"], "out of scope": ["Must-haves"], "how": ["Skills"]}
TAG = re.compile(r"^(" + "|".join(map(re.escape, TAGS)) + r"):", re.I)


def canon(label):
    return next(x for x in LABELS if x.lower() == label.lower())


def parse(text):
    """Returns (slots, questions, counts). slots maps a label to its list of items."""
    slots, counts, questions = {}, {}, []
    current, last_item, in_questions = None, None, False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^#+\s", line):
            in_questions = bool(re.match(r"^#+\s+Questions\b", line, re.I))
            current = None
            continue
        if in_questions:
            m = NUMBERED.match(line.strip())
            if m:
                questions.append(m.group(2).strip())
            elif line.strip() and questions and raw[:1].isspace():
                questions[-1] += " " + line.strip()
            continue
        m = SLOT.match(line)
        if m:
            current = canon(m.group(1))
            counts[current] = counts.get(current, 0) + 1
            slots.setdefault(current, [])
            value = m.group(2).strip()
            if value:
                slots[current].append(value)
            last_item = value or None
            continue
        if current is None:
            continue
        sub = SUB.match(line)
        if sub:
            slots[current].append(sub.group(1).strip())
            last_item = sub.group(1).strip()
        elif line.strip() and raw[:1].isspace() and last_item is not None:
            slots[current][-1] += " " + line.strip()
        elif not line.strip():
            continue
        else:
            current = None
    return slots, questions, counts


def is_bare_trap(item):
    words = [w for w in re.findall(r"[a-z]+", item.lower()) if w not in FILLER]
    return bool(words) and all(w in TRAP for w in words)


def is_none(items):
    return len(items) == 1 and items[0].strip().rstrip(".").lower() == "none"


def check(text):
    slots, questions, counts = parse(text)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("every required slot present", [f"missing slot: {s}" for s in REQUIRED if s not in counts])
    add("no slot repeated", [f"slot {s} appears {n} times" for s, n in counts.items() if n > 1])
    add("no empty slot", [f"slot {s} is empty" for s, items in slots.items() if not items])

    bad_unknown = [f"{s}: {i!r} is not 'unknown: <question>?'" for s, items in slots.items() for i in items
                   if UNKNOWN_START.match(i) and not UNKNOWN_OK.match(i)]
    add("every unknown has a question", bad_unknown)

    unknowns = slots.get("Unknowns", [])
    marked = [s for s, items in slots.items() if s != "Unknowns" and any(UNKNOWN_START.match(i) for i in items)]
    list_fails = []
    if is_none(unknowns):
        list_fails += [f"Unknowns says none but {s} is unknown" for s in marked]
    else:
        list_fails += [f"Unknowns item is not an unknown marker: {i!r}. Report only goes in If stuck, exclusions in"
                       f" Must-haves as 'out of scope:'" for i in unknowns if not UNKNOWN_START.match(i)]
    add("Unknowns list matches the slots", list_fails)

    q_fails = []
    has_unknowns = bool(marked) or (unknowns and not is_none(unknowns))
    if has_unknowns and not questions:
        q_fails.append("there are unknowns but no numbered question in a Questions block")
    if len(questions) > MAX_QUESTIONS:
        q_fails.append(f"{len(questions)} questions, at most {MAX_QUESTIONS}")
    q_fails += [f"question {n} has no question mark" for n, q in enumerate(questions, 1) if "?" not in q]
    add(f"at most {MAX_QUESTIONS} questions, each a question", q_fails)

    plan = slots.get("Plan first", [])
    add("Plan first says yes or none needed",
        [f"Plan first is {plan[0]!r}; write 'yes: <plan>' or 'none needed'" for _ in [0] if plan and not PLAN_OK.match(plan[0])])

    tag_fails = []
    for s, items in slots.items():
        for i in items:
            m = TAG.match(i)
            if m and s not in TAGS[m.group(1).lower()]:
                tag_fails.append(f"{s}: {m.group(1)!r} item belongs in {' or '.join(TAGS[m.group(1).lower()])}")
    add("tagged items in their slots", tag_fails)

    add("no default beside an unknown",
        [f"{s} offers a default beside an unknown; leave the unknown on its own" for s, items in slots.items()
         if any(re.search(r"\bunknown:", i, re.I) for i in items) and any(re.search(r"\bdefault", i, re.I) for i in items)])

    add("no bare trap adjective", [f"{s}: {i!r} names no visible signal" for s, items in slots.items()
                                   for i in items if is_bare_trap(i)])
    return results


def main(path):
    failed = False
    for name, fails in check(open(path).read()):
        print(f"{'FAIL' if fails else 'PASS'} {name}")
        for f in fails:
            print(f"  {f}")
        failed = failed or bool(fails)
    print(f"{'FAIL' if failed else 'PASS'} brief: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) == 2 else 2)
    sys.exit(main(sys.argv[1]))
