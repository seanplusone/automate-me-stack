"""Checks the shape of a brief written by the outcome skill.

Usage: python3 check/check_brief.py <brief.md>

A slot is a top-level line `- <Label>: <value>`. A note in brackets after the label is allowed, as in
`- Taste (flag, don't filter):`. Indented `  - <item>` lines under it are more items of the same slot.
The labels are fixed (see REQUIRED and OPTIONAL). Questions go in a block headed
`## Questions`, as numbered lines `1. <question>?`.

Required: Goal, Done, Output, Constraints, Tools, Agents and roles, Evals, Verification.
Optional: Kind, Plan first, Taste, Skills, Parking lot, Unknowns.

Fails when:
- a required slot is missing, or any slot label appears more than once;
- a slot has no value and no items;
- a required slot's items are only placeholders. Normalize each item first: strip bold and
  code marks, surrounding punctuation and brackets, and lowercase it. If no real word
  remains besides a placeholder token (tbd, todo, tbc, n/a, none, placeholder), the slot
  fails and the failure names it. A template hole such as `<goal here>` or `{{goal}}` is
  a placeholder. `none` alone is allowed on Skills, Parking lot and Unknowns. Tools and
  Constraints may say `none: <why>`, and the reason must contain real words. Bare `none`
  does not. `write first: none` does not name a tool;
- Evals has no real pass case or no real fail case. The label is the whole word `pass` or
  `fail` followed by `:`, or the phrase `should pass`, `must pass`, `should fail` or
  `must fail`. The text of that case must contain a real word. `Fail-safe:` is not a
  fail case;
- Plan first is present and does not start with `yes` or `none needed`;
- an `investigate:` item sits outside Done, an `out of scope:` item outside Constraints,
  or a `how:` item outside Agents and roles;
- a slot that holds `unknown:` also has a separate item that starts with `default`;
- an item that starts with `unknown` is not `unknown: <question>?` (a note may follow the question);
- the Unknowns slot is present, is not `none`, and holds an item that is not an unknown marker;
- the Unknowns slot says `none` while another slot holds an unknown marker;
- there are unknowns but no Questions block, or the block has more than 3 numbered questions,
  or a numbered question has no question mark;
- an item is only trap adjectives (modern, clean, good, better, correct, valid, nice), with no
  visible signal named.
Prints a PASS or FAIL line per check and exits 1 on any FAIL.
"""
import re
import sys

REQUIRED = ["Goal", "Done", "Output", "Constraints", "Tools", "Agents and roles", "Evals", "Verification"]
OPTIONAL = ["Kind", "Plan first", "Taste", "Skills", "Parking lot", "Unknowns"]
LABELS = REQUIRED + OPTIONAL
SLOT = re.compile(r"^- (" + "|".join(map(re.escape, LABELS)) + r")(?:\s*\([^)]*\))?:(.*)$", re.I)
SUB = re.compile(r"^\s+(?:[-*]|\d+\.)\s+(.*)$")
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
UNKNOWN_START = re.compile(r"^unknown\b", re.I)
UNKNOWN_OK = re.compile(r"^unknown:\s*[^?\s][^?]*\?", re.I)
TRAP = {"modern", "clean", "good", "better", "correct", "valid", "nice"}
FILLER = {"a", "an", "the", "it", "its", "is", "be", "should", "must", "make", "made", "very", "really", "and",
          "or", "more", "look", "looks", "feel", "feels", "pretty", "just", "kind", "of", "enough", "to", "check"}
MAX_QUESTIONS = 3
PLAN_OK = re.compile(r"^(yes\b|none needed\b)", re.I)
TAGS = {"investigate": ["Done"], "out of scope": ["Constraints"], "how": ["Agents and roles"]}
TAG = re.compile(r"^(" + "|".join(map(re.escape, TAGS)) + r"):", re.I)
FENCE_MARK = re.compile(r"^(```+|~~~+)")
PLACEHOLDER_WORDS = {"tbd", "todo", "tbc", "n/a", "n.a.", "na", "none", "placeholder"}
NON_CONTENT = FILLER | {"later", "here", "below", "above"}
NONE_OK = {"Skills", "Parking lot", "Unknowns"}
NONE_REASON = {"Tools", "Constraints"}
CASE_LABEL = re.compile(r"(?<![\w-])(pass|fail)\s*:", re.I)
CASE_PHRASE = re.compile(r"\b(?:should|must)\s+(pass|fail)\b", re.I)
MARKER_WORDS = {"pass", "fail", "should", "must"}
WRITE_FIRST_NONE = re.compile(r"^write first:\s*none\.?$", re.I)
NONE_WHY = re.compile(r"^none:\s*(.*)$", re.I)
TEMPLATE_HOLE = re.compile(r"^(?:<[^<>\n]+>|\{\{[^{}\n]+\}\})$")
DEFAULT_ITEM = re.compile(r"^default\b", re.I)


def canon(label):
    """The canonical label, or None when the text is not one of the known slots."""
    folded = label.casefold()
    for name in LABELS:
        if name.casefold() == folded:
            return name
    return None


def parse(text):
    """Returns (slots, questions, counts). slots maps a label to its list of items."""
    slots, counts, questions = {}, {}, []
    current, last_item, in_questions, fence = None, None, False, None
    for raw in text.splitlines():
        line = raw.rstrip()
        marker = FENCE_MARK.match(line.strip())
        if fence:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= fence[1]:
                fence = None
            continue
        if marker:
            fence = (marker.group(1)[0], len(marker.group(1)))
            continue
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
            if current is None:
                continue
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


def strip_markup(text):
    text = re.sub(r"\*\*|__", "", text)
    text = text.replace("`", "")
    return re.sub(r"\s*/\s*", "/", text).strip()


def unwrap(text):
    prev = None
    while text != prev:
        prev = text
        text = text.strip().strip("\"'*_.,!;?:!")
        if len(text) >= 2 and (text[0], text[-1]) in {("(", ")"), ("[", "]")}:
            text = text[1:-1]
    return text.strip()


def content_words(text):
    raw = unwrap(strip_markup(text)).casefold()
    words = re.findall(r"[a-z0-9]+(?:/[a-z0-9]+)?", raw)
    return [w for w in words if w not in NON_CONTENT and w not in PLACEHOLDER_WORDS and any(ch.isalpha() for ch in w)]


def is_placeholder(item, slot):
    """True when the item has no real content for this slot.

    Markup, surrounding punctuation and brackets are stripped first. A template hole
    (`<...>`, `{{...}}`) is a placeholder. So is text whose only words are placeholder
    tokens. `none: <why>` is real on Tools and Constraints when the reason has a real word.
    `write first: none` does not name a tool.
    """
    text = item.strip()
    plain = strip_markup(text)
    if TEMPLATE_HOLE.match(plain.strip().strip("\"'`")):
        return True
    if slot == "Tools" and WRITE_FIRST_NONE.match(unwrap(plain)):
        return True
    reason = NONE_WHY.match(unwrap(plain))
    if reason and slot in NONE_REASON:
        return not content_words(reason.group(1))
    if not content_words(plain):
        core = unwrap(plain).casefold().rstrip(".")
        return not (core == "none" and slot in NONE_OK)
    return False


def eval_cases(item):
    """Pass and fail cases in one item. A colon label is a whole word plus `:`.

    `should pass` and `must pass` (and the fail forms) count too. The body is empty
    when nothing real follows the label.
    """
    text = strip_markup(item)
    marks = list(CASE_LABEL.finditer(text))
    if marks:
        found = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
            found.append((m.group(1).lower(), text[m.end():end]))
        return found
    found = []
    for m in CASE_PHRASE.finditer(text):
        found.append((m.group(1).lower(), text))
    return found


def case_is_real(body):
    return any(w not in MARKER_WORDS for w in content_words(body))


def check(text):
    slots, questions, counts = parse(text)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("every required slot present", [f"missing slot: {s}" for s in REQUIRED if s not in counts])
    add("no slot repeated", [f"slot {s} appears {n} times" for s, n in counts.items() if n > 1])
    add("no empty slot", [f"slot {s} is empty" for s, items in slots.items() if not items])
    add("no required slot is only a placeholder",
        [f"slot {s} is only a placeholder" for s in REQUIRED if s in slots and slots[s]
         and all(is_placeholder(i, s) for i in slots[s])])

    evals = slots.get("Evals", [])
    eval_fails = []
    if evals and not all(is_placeholder(i, "Evals") for i in evals):
        kinds = {kind for item in evals for kind, body in eval_cases(item) if case_is_real(body)}
        if "pass" not in kinds:
            eval_fails.append("Evals has no pass case")
        if "fail" not in kinds:
            eval_fails.append("Evals has no fail case")
    add("Evals has a pass and a fail", eval_fails)

    bad_unknown = [f"{s}: {i!r} is not 'unknown: <question>?'" for s, items in slots.items() for i in items
                   if UNKNOWN_START.match(i) and not UNKNOWN_OK.match(i)]
    add("every unknown has a question", bad_unknown)

    unknowns = slots.get("Unknowns", [])
    marked = [s for s, items in slots.items() if s != "Unknowns" and any(UNKNOWN_START.match(i) for i in items)]
    list_fails = []
    if "Unknowns" in counts:
        if is_none(unknowns):
            list_fails += [f"Unknowns says none but {s} is unknown" for s in marked]
        else:
            list_fails += [f"Unknowns item is not an unknown marker: {i!r}. Report only goes in Constraints, exclusions in"
                           f" Constraints as 'out of scope:'" for i in unknowns if not UNKNOWN_START.match(i)]
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
         if any(UNKNOWN_START.match(i) for i in items) and any(DEFAULT_ITEM.match(i.strip()) for i in items)])

    add("no bare trap adjective", [f"{s}: {i!r} names no visible signal" for s, items in slots.items()
                                   for i in items if is_bare_trap(i)])
    return results


def main(path):
    failed = False
    with open(path) as handle:
        text = handle.read()
    for name, fails in check(text):
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
