"""Checks the shape of a brief written by the outcome skill.

Usage: python3 check/check_brief.py <brief.md>

A slot is a top-level line `- <Label>: <value>`. A note in brackets after the label is allowed, as in
`- Taste (flag, don't filter):`. Indented `  - <item>` lines under it are more items of the same slot.
The labels are fixed (see REQUIRED and OPTIONAL). Questions go in a block headed
`## Questions`, as numbered lines `1. <question>?`.

Required: Goal, Done, Output, Constraints, Tools, Agents and roles, Evals, Verification.
Optional: Kind, Plan first, Taste, Skills, Parking lot, Unknowns.

Each value gets one of three outcomes from classify(value):
- fail: after stripping bold and code marks, one leading tag label (write first:, investigate:,
  out of scope:, how:, none:, pass:, fail:, todo:) and surrounding punctuation and brackets, nothing
  is left, or only words from this fixed list: tbd, tbc, tba, todo, fixme, xxx, n/a, na, none, pending,
  placeholder, later, to be determined, to be decided, to be confirmed, fill in, fill in later,
  see below, see above, same as above. A template hole anywhere also fails: `<goal>` (nesting
  allowed), `{{x}}`, `{x}`, `${x}` or `[insert x]`. Holes inside `code` marks, autolinks such as
  `<https://...>` and comparisons such as `p95 < 200ms` are not holes.
- ask: not on the list, but suspicious. The value is only symbols, with no letter or digit
  (`->`); or only hedges (it depends, depends, we'll see, we will see, not sure, unsure, maybe,
  perhaps, idk, dunno); or a single word of one or two letters (`ok`, `x`).
- pass: anything else. Words are Unicode, so `上线第二版。` is real. So are `make`, `$500`, `#123` and `24`.

The list is deliberately narrow. check_brief catches common placeholders and template holes. A
needs-human value (exit 2, one ASK line each) is the break point where the agent stops and asks
the person. The read-back catches the rest.

Fails (exit 1) when:
- a required slot is missing, or any slot label appears more than once;
- a slot has no value and no items;
- every item of a required slot classifies as fail. `none` alone may sit on Skills, Parking lot
  and Unknowns. `none: <why>` is real when the reason is. `write first: none` alone does not name a tool;
- any item in any slot holds a template hole (Questions lines are not checked);
- Kind is present and is not one of build, review, design, learn, search/decide;
- Evals has no pass case or no fail case whose body is not fail. A label is the whole word `pass`
  or `fail` followed by `:`, or `should|must pass|fail`, anywhere in an item. A colon label's body
  runs to the next label, and a phrase's body is the text before it. `Fail-safe:` is not a fail case.
  An `unknown: <question>?` item in Evals satisfies this instead, when the Questions block has a question;
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

Asks (exit 2, when nothing fails) for each item of a required slot, or each Evals case body, that
classifies as ask. It prints `ASK: <slot>: Is '<value>' a real answer for <slot>?`. When the person
says yes, record it in a `## Confirmed` block, one `- <Slot>: <value>` line each, and rerun. That
value then passes. When the person says no, replace the value.

Prints a PASS or FAIL line per check, then the ASK lines, then `PASS|FAIL|ASK brief: <path>`.
Exit 0 pass, 1 fail, 2 ask, 3 usage.

Exported for other skills: classify(value) -> "pass"|"fail"|"ask", is_placeholder(value),
eval_cases(item) -> [(kind, body)], case_is_real(body), check(text) -> [(name, fails)],
asks(text) -> [(slot, value)], parse(text) and core(value).
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
KINDS = {"build", "review", "design", "learn", "search/decide"}
CASE_LABEL = re.compile(r"(?<![\w-])(pass|fail)\s*:", re.I)
CASE_PHRASE = re.compile(r"\b(?:should|must)\s+(pass|fail)\b", re.I)
DEFAULT_ITEM = re.compile(r"^default\b", re.I)
WORD = re.compile(r"[^\W_]")
CODE_SPAN = re.compile(r"`+[^`\n]*`+")
HOLE = re.compile(r"<(?![^<>\n]*(?://|@))[^\W\d_][^<>\n]*>|\{[^{}\n]*[^\W\d_][^{}\n]*\}|\[\s*insert\b[^\]\n]*\]", re.I)
LEAD_TAG = re.compile(r"^(?:write first|investigate|out of scope|how|none|pass|fail|todo)\s*:", re.I)
PLACEHOLDERS = ["to be determined", "to be decided", "to be confirmed", "fill in later", "fill in", "see below",
                "see above", "same as above", "tbd", "tbc", "tba", "todo", "fixme", "xxx", "n/a", "n.a.", "na", "none",
                "pending", "placeholder", "later"]
HEDGES = ["it depends", "depends", "we'll see", "we will see", "not sure", "unsure", "maybe", "perhaps", "idk", "dunno"]


def phrases(words):
    return re.compile(r"(?<![^\W_])(?:" + "|".join(map(re.escape, words)) + r")(?![^\W_])")


PLACEHOLDER = phrases(PLACEHOLDERS)
HEDGE = phrases(HEDGES)
SHORT = re.compile(r"[^\W\d_]{1,2}")

def canon(label):
    """The canonical label, or None when the text is not one of the known slots."""
    folded = label.casefold()
    for name in LABELS:
        if name.casefold() == folded:
            return name
    return None


def parse(text):
    """Returns (slots, questions, counts, confirmed). slots maps a label to its list of items.

    confirmed holds a (slot, value) key for each `- <Slot>: <value>` line under `## Confirmed`.
    """
    slots, counts, questions, confirmed = {}, {}, [], set()
    current, last_item, section, fence = None, None, None, None
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
            heading = re.match(r"^#+\s+(Questions\b|Confirmed\s*$)", line, re.I)
            section = heading.group(1).split()[0].lower() if heading else None
            current = None
            continue
        if section == "confirmed":
            m = SLOT.match(line)
            if m and canon(m.group(1)):
                confirmed.add(confirmed_key(canon(m.group(1)), m.group(2)))
            continue
        if section == "questions":
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
    return slots, questions, counts, confirmed


def is_bare_trap(item):
    words = [w for w in re.findall(r"[a-z]+", item.lower()) if w not in FILLER]
    return bool(words) and all(w in TRAP for w in words)


def is_none(items):
    return len(items) == 1 and items[0].strip().rstrip(".").lower() == "none"


def strip_markup(text):
    text = re.sub(r"\*\*|__", "", text).replace("`", "").replace("’", "'")
    return re.sub(r"\s*/\s*", "/", text).strip()


def unwrap(text):
    prev = None
    while text != prev:
        prev = text
        text = text.strip().strip("\"'*_.,!;?:-–—")
        if len(text) >= 2 and (text[0], text[-1]) in {("(", ")"), ("[", "]")}:
            text = text[1:-1]
    return text.strip()


def core(value):
    """The value as classify() sees it: markup, one leading tag label and surrounding punctuation gone, casefolded."""
    return " ".join(unwrap(LEAD_TAG.sub("", unwrap(strip_markup(value)), count=1)).casefold().split())


def classify(value):
    """'fail', 'ask' or 'pass' for one value. See the module docstring for the rule."""
    if HOLE.search(CODE_SPAN.sub(" ", value)):
        return "fail"
    text = core(value)
    if not text:
        return "fail"
    rest = PLACEHOLDER.sub(" ", text)
    if not WORD.search(rest):
        return "fail" if rest != text else "ask"
    if not WORD.search(HEDGE.sub(" ", rest)) or SHORT.fullmatch(text):
        return "ask"
    return "pass"


def is_placeholder(value):
    return classify(value) == "fail"


def eval_cases(item):
    """(kind, body) for each pass or fail case in one Evals item.

    A label is `pass:` or `fail:` as a whole word, or `should|must pass|fail`, anywhere in the item.
    A colon label's body runs to the next label. A phrase's body is the text before it, back to the
    previous label.
    """
    text = re.sub(r"\*\*|__", "", item)
    marks = sorted([(m.start(), m.end(), m.group(1).lower(), True) for m in CASE_LABEL.finditer(text)]
                   + [(m.start(), m.end(), m.group(1).lower(), False) for m in CASE_PHRASE.finditer(text)])
    found = []
    for i, (start, end, kind, colon) in enumerate(marks):
        if colon:
            found.append((kind, text[end:marks[i + 1][0] if i + 1 < len(marks) else len(text)]))
        else:
            found.append((kind, text[marks[i - 1][1] if i else 0:start]))
    return found


def case_is_real(body):
    return classify(body) == "pass"


def confirmed_key(slot, value):
    return slot, core(value)


def asks(text):
    """(slot, value) for each value in a required slot that needs a person to confirm it."""
    slots, _, _, confirmed = parse(text)
    found = []
    for s in REQUIRED:
        for item in slots.get(s, []):
            if UNKNOWN_START.match(item):
                continue
            values = [body for _, body in eval_cases(item)] if s == "Evals" and eval_cases(item) else [item]
            for v in values:
                if classify(v) == "ask" and confirmed_key(s, v) not in confirmed and confirmed_key(s, item) not in confirmed:
                    found.append((s, unwrap(strip_markup(v))))
    return found

def check(text):
    slots, questions, counts, _ = parse(text)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("every required slot present", [f"missing slot: {s}" for s in REQUIRED if s not in counts])
    add("no slot repeated", [f"slot {s} appears {n} times" for s, n in counts.items() if n > 1])
    add("no empty slot", [f"slot {s} is empty" for s, items in slots.items() if not items])
    add("no required slot is only a placeholder",
        [f"slot {s} is only a placeholder" for s in REQUIRED if s in slots and slots[s]
         and all(is_placeholder(i) for i in slots[s])])
    add("no template hole", [f"{s}: {i!r} holds a template hole; fill it" for s, items in slots.items() for i in items
                             if HOLE.search(CODE_SPAN.sub(" ", i))])
    kind = slots.get("Kind", [])
    add("Kind is one kind", [f"Kind is {kind[0]!r}; write one of {', '.join(sorted(KINDS))}"
                             for _ in [0] if kind and core(kind[0]) not in KINDS])

    evals = slots.get("Evals", [])
    eval_fails = []
    if evals and not all(is_placeholder(i) for i in evals) and not (any(UNKNOWN_START.match(i) for i in evals) and questions):
        kinds = {kind for item in evals for kind, body in eval_cases(item) if not is_placeholder(body)}
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
    with open(path) as handle:
        text = handle.read()
    failed = False
    for name, fails in check(text):
        print(f"{'FAIL' if fails else 'PASS'} {name}")
        for f in fails:
            print(f"  {f}")
        failed = failed or bool(fails)
    asked = asks(text)
    for slot, value in asked:
        print(f"ASK: {slot}: Is '{value}' a real answer for {slot}?")
    verdict = "FAIL" if failed else "ASK" if asked else "PASS"
    print(f"{verdict} brief: {path}")
    return {"FAIL": 1, "ASK": 2, "PASS": 0}[verdict]


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) == 2 else 3)
    sys.exit(main(sys.argv[1]))
