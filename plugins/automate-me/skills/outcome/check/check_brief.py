"""Checks the shape of a brief written by the outcome skill.

Usage: python3 check/check_brief.py <brief.md>

A slot is a top-level line `- <Label>: <value>`. A note in brackets after the label is allowed, as in
`- Taste (flag, don't filter):`. Indented `  - <item>` lines under it are more items of the same slot.
The labels are fixed (see REQUIRED and OPTIONAL). Questions go in a block headed
`## Questions`, as numbered lines `1. <question>?`.

Required: Goal, Done, Output, Constraints, Tools, Agents and roles, Evals, Verification.
Optional: Kind, Plan first, Taste, Skills, Parking lot, Unknowns.

Each value gets one of three outcomes from classify(value). core(value) is the value as classify sees
it: NFKC, emphasis and code marks gone, one leading tag label (write first:, investigate:,
out of scope:, how:, none:, pass:, fail:, todo:) and surrounding punctuation and brackets gone,
dots dropped from a dotted initialism (T.B.D.), and `-`, `_` or `.` between letters read as a space.
- fail, only when unambiguous:
  - nothing is left;
  - only words from this fixed list are left, with or without hedge words other than `not`: tbd, tbc, tba, todo,
    fixme, xxx, n/a, na, none, pending, placeholder, later, to be determined, to be decided,
    to be confirmed, fill in, fill in later, see below, see above, same as above;
  - the value is nothing but template holes: `<goal>`, `< goal >`, `{{x}}`, `{x}`, `${x}`, `{}`.
    `{2,4}` holds no letter, so it is not a hole;
  - `[insert x]` appears anywhere;
  - the value is a line of the template in SKILL.md.
- ask, when in doubt:
  - every word is a hedge word: maybe, perhaps, possibly, probably, not, sure, unsure, unclear,
    depends, depending, it, idk, dunno, we, ll, will, well, see, yet, tbh, hmm, let, s;
  - the value is only symbols that are not stripped punctuation, such as `→` or an emoji;
  - the value is one word of one or two letters (`ok`, `x`);
  - a hole sits inside a longer value (`Press <Enter> to submit.`). This asks
    "Is '<value>' a real answer for <slot>, or a hole to fill?".
  Code spans and autolinks (`<https://...>`, `<tel:...>`, `<a@b.c>`) are never holes. `a < b`
  with a space after `<` is a comparison, not a hole.
- pass: anything else. Words are Unicode, so `上线第二版。` is real. So are `make`, `$500`, `#123` and `24`.

The rule is deliberately narrow. check_brief FAILs only what is unambiguous. When in doubt it ASKs
(exit 2, one ASK line each), and the agent stops and asks the person. Asking is cheap, and a wrong
FAIL blocks a real brief. The read-back catches the rest.
It is a review aid, not a gate on meaning. README.md lists the known misses.

Fails (exit 1) when:
- a required slot is missing, or any slot label appears more than once;
- a slot has no value and no items;
- any item of any slot, or any Evals case body, classifies as fail. `none` alone is allowed on
  Skills, Parking lot and Unknowns, and as one item beside others (`write first: none`).
  `none: <why>` is real when the reason is;
- Kind is present and is not one of build, review, design, learn, search/decide;
- Plan first is present and does not start with `yes` or `none needed`;
- an `investigate:` item sits outside Done, an `out of scope:` item outside Constraints,
  or a `how:` item outside Agents and roles;
- a slot that holds an unknown marker also has a separate item that starts with `default`;
- an unknown marker is not `unknown: <question>?` (a note may follow the question). An unknown
  marker is an item that is `unknown` alone or starts with `unknown:`. `Unknown column names` is text;
- the Unknowns slot is present, is not `none`, and holds an item that is not an unknown marker;
- the Unknowns slot says `none` while another slot holds an unknown marker;
- there are unknowns but no Questions block, or the block has more than 3 numbered questions,
  or a numbered question has no question mark;
- an item is only trap adjectives (modern, clean, good, better, correct, valid, nice) and names no
  visible signal. A digit is a visible signal.

Evals cases: a label is the whole word `pass` or `fail` followed by `:`, or `should|must pass|fail`,
anywhere in an item outside code spans. A colon label's body runs to the next label, and a phrase's
body is the text before it. A phrase whose body is blank, as one that starts the item or follows another
label, is not a case, so `Should fail if the price is missing.` alone has no case. In an item that
starts with a colon label, a phrase counts only when it ends the item, so `Fail: a row that should pass the price rule is dropped.` has no pass case. Text
before an item's first colon label is judged too.
`Fail-safe:` is not a fail case.

Asks (exit 2, when nothing fails):
- for each item of a required slot, and each Evals case body, that classifies as ask, and for a
  hole inside a longer value in any slot. It prints `ASK: <slot>: Is '<value>' a real answer for
  <slot>?`. When the person says yes, record it in a `## Confirmed` block (that exact heading), one
  `- <Slot>: <value>` line each, and rerun. That value then passes. A confirmation is per item, or
  per Evals case body. When the person says no, replace the value;
- when Evals has real content but no pass case or no fail case can be found, unless it holds an
  `unknown: <question>?` item and the brief has a Questions block. It prints
  `ASK: Evals: Is there a pass case and a fail case here?`. On a yes, label them `Pass:` and `Fail:`.

Prints a PASS or FAIL line per check, then the ASK lines, then `PASS|FAIL|ASK brief: <path>`.
Exit 0 pass, 1 fail, 2 ask, 3 usage (bad arguments, or a file that is missing or not UTF-8 text).

Exported for other skills: classify(value) -> "pass"|"fail"|"ask", judge(value) -> (outcome, why),
is_placeholder(value), eval_cases(item) -> [(kind, body)], case_is_real(body),
check(text) -> [(name, fails)], asks(text) -> [(slot, value)], ask_lines(text), parse(text), core(value).
"""
import os
import re
import sys
import unicodedata

REQUIRED = ["Goal", "Done", "Output", "Constraints", "Tools", "Agents and roles", "Evals", "Verification"]
OPTIONAL = ["Kind", "Plan first", "Taste", "Skills", "Parking lot", "Unknowns"]
LABELS = REQUIRED + OPTIONAL
NONE_OK = {"Skills", "Parking lot", "Unknowns"}
SLOT = re.compile(r"^- (" + "|".join(map(re.escape, LABELS)) + r")(?:\s*\([^)]*\))?:(.*)$", re.I)
OTHER_SLOT = re.compile(r"^[-*+][ \t]+(\S[^:\uff1a\n]{0,59}?)\s*(?:(?<!\d)[:\uff1a]|[:\uff1a](?!\d))(?!//)")
SUB = re.compile(r"^\s+(?:[-*]|\d+\.)\s+(.*)$")
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
UNKNOWN_START = re.compile(r"^unknown(?:\s*:|\W*$)", re.I)
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
ITEM_END = re.compile(r"[\s.!]*$")
STARTS_WITH_LABEL = re.compile(r"^[\W_]*(?:pass|fail)\s*:", re.I)
DEFAULT_ITEM = re.compile(r"^default\b", re.I)
WORD = re.compile(r"[^\W_]+")
SHORT = re.compile(r"[^\W\d_]{1,2}")
LEAD_TAG = re.compile(r"^(?:write first|investigate|out of scope|how|none|pass|fail|todo)\s*:", re.I)

CODE = r"(?P<tick>`+)(?!`).*?(?<!`)(?P=tick)(?!`)"
AUTOLINK = r"<[A-Za-z][A-Za-z0-9+.-]*:[^<>\s]*>|<[^<>\s@]+@[^<>\s]+>"
HOLE = r"<[^\W\d_][^<>\n]*(?<!\s)>|\$?\{[^{}\n]*[^\W\d_][^{}\n]*\}"
LOOSE_HOLE = r"<[^<>\n]*[^\W\d_][^<>\n]*>|\$?\{[^{}\n]*[^\W\d_][^{}\n]*\}|\$?\{\s*\}"
INSERT = r"\[\s*insert\b[^\]\n]*\]"
CODE_SPAN = re.compile(CODE)

EMPHASIS = re.compile(r"\*|~~|(?<![^\W_])_+|_+(?![^\W_])")
INITIALISM = re.compile(r"(?<![^\W_.])[^\W\d_](?:\.[^\W\d_])+(?![^\W_])")
SEPARATOR = re.compile(r"(?<=[^\W\d_])[-_.](?=[^\W\d_])")
PLACEHOLDERS = ["to be determined", "to be decided", "to be confirmed", "fill in later", "fill in", "see below",
                "see above", "same as above", "tbd", "tbc", "tba", "todo", "fixme", "xxx", "n/a", "n.a.", "na", "none",
                "pending", "placeholder", "later"]
HEDGE_WORDS = {"maybe", "perhaps", "possibly", "probably", "not", "sure", "unsure", "unclear", "depends", "depending",
               "it", "idk", "dunno", "we", "ll", "will", "well", "see", "yet", "tbh", "hmm", "let", "s"}


def unwrap(text):
    prev = None
    while text != prev:
        prev = text
        text = text.strip().strip("\"'“”‘’«»*_.,!;?:-–—")
        if len(text) >= 2 and (text[0], text[-1]) in {("(", ")"), ("[", "]")}:
            text = text[1:-1]
    return text.strip()


def core(value):
    """The value as classify() sees it. See the module docstring."""
    text = unicodedata.normalize("NFKC", value).replace("`", "").replace("’", "'")
    text = " ".join(re.sub(r"\s*/\s*", "/", EMPHASIS.sub("", text)).split())
    tagless = LEAD_TAG.sub("", text, count=1)
    text = unwrap(tagless if tagless != text else LEAD_TAG.sub("", unwrap(text), count=1))
    text = SEPARATOR.sub(" ", INITIALISM.sub(lambda m: m.group().replace(".", ""), text))
    return " ".join(text.casefold().split())


PLACEHOLDER = re.compile(r"(?<![^\W_])(?:" + "|".join(sorted({re.escape(core(p)) for p in PLACEHOLDERS}, key=len, reverse=True))
                         + r")(?![^\W_])")


def outside_code(pattern):
    """A regex whose `keep` group matches a code span or autolink, so callers can skip them."""
    return re.compile(rf"(?P<keep>{CODE}|{AUTOLINK})|{pattern}", re.I)


HOLE_FINDER, LOOSE_FINDER, INSERT_FINDER = outside_code(HOLE), outside_code(LOOSE_HOLE), outside_code(INSERT)


def found(finder, value):
    return any(m.group("keep") is None for m in finder.finditer(value))


def unholed(value):
    """The value with every hole outside code removed, innermost first, so nested holes go too."""
    prev = None
    while value != prev:
        prev, value = value, LOOSE_FINDER.sub(lambda m: m.group("keep") or " ", value)
    return value


def canon(label):
    """The canonical label, or None when the text is not one of the known slots."""
    folded = label.casefold()
    for name in LABELS:
        if name.casefold() == folded:
            return name
    return None


def parse(text):
    """Returns (slots, questions, counts, confirmed). slots maps a label to its list of items.

    counts also holds a top-level `- <Label>:` line whose label is not a known slot, so check can fail it.

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
            section = "confirmed" if line == "## Confirmed" else "questions" if re.match(r"^#+\s+Questions\b", line, re.I) else None
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
        other = OTHER_SLOT.match(line)
        if other:
            current = None
            name = re.sub(r"\s*\([^)]*\)$", "", other.group(1))
            if canon(name):
                name = f"{name} (write it as '- {canon(name)}:')"
            counts[name] = counts.get(name, 0) + 1
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


def template_values():
    """core() of every value in the brief template in SKILL.md, pasted unfilled."""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md"), encoding="utf-8") as handle:
        block = handle.read().split("```\n# Brief: <short title>\n", 1)[1].split("```", 1)[0]
    return {core(v) for items in parse(block)[0].values() for v in items}


TEMPLATE = template_values()


def judge(value):
    """(outcome, why) for one value. outcome is 'fail', 'ask' or 'pass'. why is 'hole' when a template
    hole decided it, 'placeholder' for any other fail, 'value' for any other ask, and None on a pass."""
    text = core(unholed(value))
    if found(INSERT_FINDER, value) or core(value) in TEMPLATE or (not text and unholed(value) != value):
        return "fail", "hole"
    if not text:
        return "fail", "placeholder"
    rest = PLACEHOLDER.sub(" ", text)
    words = WORD.findall(rest)
    if all(w in HEDGE_WORDS for w in words):
        return ("fail", "placeholder") if rest != text and "not" not in words else ("ask", "value")
    if found(HOLE_FINDER, value):
        return "ask", "hole"
    if SHORT.fullmatch(text):
        return "ask", "value"
    return "pass", None


def classify(value):
    """'fail', 'ask' or 'pass' for one value. See the module docstring for the rule."""
    return judge(value)[0]


def is_placeholder(value):
    return classify(value) == "fail"


def case_marks(item):
    """(text, marks) for one Evals item: text without bold marks, and (start, end, kind, colon) for each label."""
    text = re.sub(r"\*\*|__", "", item)
    scan = CODE_SPAN.sub(lambda m: "x" * len(m.group()), text)
    labelled = STARTS_WITH_LABEL.match(scan)
    return text, sorted([(m.start(), m.end(), m.group(1).lower(), True) for m in CASE_LABEL.finditer(scan)]
                        + [(m.start(), m.end(), m.group(1).lower(), False) for m in CASE_PHRASE.finditer(scan)
                           if not labelled or ITEM_END.match(scan, m.end())])


def eval_cases(item):
    """(kind, body) for each pass or fail case in one Evals item. See the module docstring."""
    text, marks = case_marks(item)
    found_cases = []
    for i, (start, end, kind, colon) in enumerate(marks):
        if colon:
            found_cases.append((kind, text[end:marks[i + 1][0] if i + 1 < len(marks) else len(text)]))
        else:
            body = text[marks[i - 1][1] if i else 0:start]
            found_cases += [(kind, body)] * bool(core(body))
    return found_cases


def eval_lead(item):
    """The text before an Evals item's first label, when that label is a colon label. A phrase case already owns it."""
    text, marks = case_marks(item)
    return text[:marks[0][0]] if marks and marks[0][3] else ""


def case_is_real(body):
    return classify(body) == "pass"


def confirmed_key(slot, value):
    return slot, core(value)


def shown(value, item):
    """The value as written. A case body drops the separator that ends it before the next label."""
    return value.strip() if value is item else value.strip().rstrip(";,").strip()


def judged(slots):
    """(slot, item, value, outcome, why) for every value: each item, or each case body of an Evals item."""
    out = []
    for s, items in slots.items():
        for item in items:
            cases = eval_cases(item) if s == "Evals" else []
            lead = eval_lead(item) if cases else ""
            for v in [lead] * bool(core(lead)) + [body for _, body in cases] or [item]:
                outcome, why = judge(v)
                if outcome == "fail" and v is item and core(v) == "none" and (s in NONE_OK or len(items) > 1):
                    outcome, why = "pass", None
                out.append((s, item, v, outcome, why))
    return out


def evals_need_cases(slots, questions, values):
    """True when Evals has real content but no pass case or no fail case can be found."""
    evals = slots.get("Evals", [])
    if not evals or any(s == "Evals" and o == "fail" for s, _, _, o, _ in values):
        return False
    if any(UNKNOWN_START.match(i) for i in evals) and questions:
        return False
    kinds = {kind for item in evals for kind, _ in eval_cases(item)}
    return not {"pass", "fail"} <= kinds


def found_asks(text):
    """(slot, value, ASK line) for each value that needs a person to confirm it."""
    slots, questions, _, confirmed = parse(text)
    values = judged(slots)
    out = []
    for s, item, v, outcome, why in values:
        if outcome != "ask" or UNKNOWN_START.match(item) or (s not in REQUIRED and why != "hole"):
            continue
        if confirmed_key(s, v) in confirmed:
            continue
        hole = ", or a hole to fill" if why == "hole" else ""
        out.append((s, shown(v, item), f"ASK: {s}: Is '{shown(v, item)}' a real answer for {s}{hole}?"))
    if evals_need_cases(slots, questions, values):
        out.append(("Evals", "; ".join(slots["Evals"]), "ASK: Evals: Is there a pass case and a fail case here?"))
    return out


def asks(text):
    """(slot, value) for each value that needs a person to confirm it."""
    return [(s, v) for s, v, _ in found_asks(text)]


def ask_lines(text):
    return [line for _, _, line in found_asks(text)]


def is_bare_trap(item):
    if re.search(r"\d", item):
        return False
    words = [w for w in re.findall(r"[a-z]+", item.lower()) if w not in FILLER]
    return bool(words) and all(w in TRAP for w in words)


def is_none(items):
    return len(items) == 1 and items[0].strip().rstrip(".").lower() == "none"


def check(text):
    slots, questions, counts, _ = parse(text)
    values = judged(slots)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("every required slot present", [f"missing slot: {s}" for s in REQUIRED if s not in counts])
    add("no unknown slot", [f"unknown slot: {s}. Use only {', '.join(LABELS)}. Indent a slot's items under it" for s in counts if s not in LABELS])
    add("no slot repeated", [f"slot {s} appears {n} times" for s, n in counts.items() if n > 1])
    add("no empty slot", [f"slot {s} is empty" for s, items in slots.items() if not items])
    place = []
    for s, items in slots.items():
        mine = [(v, o, why) for slot, _, v, o, why in values if slot == s]
        if mine and all(o == "fail" for _, o, _ in mine):
            place.append(f"slot {s} is only a placeholder")
        else:
            place += [f"{s}: {shown(v, v)!r} is a placeholder" for v, o, why in mine if o == "fail" and why == "placeholder"]
    add("no placeholder", place)
    add("no template hole", [f"{s}: {shown(v, v)!r} is a template hole; fill it" for s, _, v, o, why in values
                             if o == "fail" and why == "hole"])
    kind = slots.get("Kind", [])
    add("Kind is one kind", [f"Kind is {kind[0]!r}; write one of {', '.join(sorted(KINDS))}"
                             for _ in [0] if kind and core(kind[0]) not in KINDS])

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
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError) as err:
        print(f"usage: cannot read {path}: {err.strerror if isinstance(err, OSError) else 'not UTF-8 text'}", file=sys.stderr)
        return 3
    failed = False
    for name, fails in check(text):
        print(f"{'FAIL' if fails else 'PASS'} {name}")
        for f in fails:
            print(f"  {f}")
        failed = failed or bool(fails)
    asked = ask_lines(text)
    for line in asked:
        print(line)
    verdict = "FAIL" if failed else "ASK" if asked else "PASS"
    print(f"{verdict} brief: {path}")
    return {"FAIL": 1, "ASK": 2, "PASS": 0}[verdict]


if __name__ == "__main__":
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__.strip())
        sys.exit(0)
    if len(sys.argv) != 2:
        print("usage: python3 check/check_brief.py <brief.md>", file=sys.stderr)
        sys.exit(3)
    sys.exit(main(sys.argv[1]))
