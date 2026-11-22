"""Checks a decisions.md written by the shape-idea skill.

Usage: python3 check/check_decisions.py <decisions.md> [--confirmed <confirmed.md>]

There are three outcomes.

1. FORMAT INVALID, exit 1. Only what the script knows for certain (see "Format invalid" below).
2. CHECK WITH ME, exit 2, when the format is valid. One list of values the script cannot be sure about. The agent
   shows each item to the person and records each yes in confirmed.md.
3. PASS, exit 0, when the format is valid and every item on the list has a yes.

Sections are `## Decided`, `## Open`, `## Parked`, and `## Handoff`, in that order, each once.
An item is one top-level bullet (`- ` or `* `). A later physical line under a section is an item
that ran past one line. A section whose only item is `none` has no items. Handoff holds:

    - next: /automate-me:outcome
    - stop: done | turn-cap | open-cap
    - turns: <n>
    - writing: pass

The five slots are goal, done, output, verify, and constraints. A slot counts when a Decided
or Open item starts with `<slot>:`. An Open example is `output: what comes back, a list or a page?`.
A slot in Parked does not count. A line such as `goalpost:` is not the goal slot. Section, slot and field
names are ASCII: `## Decıded` with a dotless i is not the Decided heading, so the section is missing.

The open cap counts Open items that are not those five slots. `stop: open-cap` is valid only
when that count is more than 5 and `turns` is from 2 through 10. It is never valid on turn 1.
`stop: turn-cap` is valid only when `turns` is 10. `stop: done` is valid only when all five
slots are Decided lines and none of them is also Open.

`turns` is parsed as ASCII digits only (`^[0-9]+$`), from 1 through 10.

A value is blank when nothing is left once `stated:` labels, markup and punctuation go (`goal: stated:`).

Format invalid (exit 1) when:
- the file has no `# Decisions` title;
- a section is missing or repeated, or the sections are out of order;
- a code fence is not closed, or sits under Decided, Open or Parked, because its text would not reach the brief;
- a slot is missing from both Decided and Open, is repeated, is in both, or is blank. A blank value is also on the
  CHECK WITH ME list, with a suggestion. A slot written as `**goal:**` or `1. goal:` gets its own message;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line is blank or
  repeated, or another Decided or Parked line is blank;
- a value is untouched template text: a template hole such as `<goal>`, a line of the template left unfilled, or a
  word from outcome's fixed placeholder list such as TBD, TODO or N/A (check_brief's judge() says fail). `none` is
  not on this list here: it is on the CHECK WITH ME list;
- an Open item is only a placeholder or only a hole (`TBD?`, `?`, `<question>?`);
- stop is missing, repeated, not one of done, turn-cap, open-cap, or does not match the file;
- turns is missing, repeated, or not a whole number from 1 through 10;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line, no single `writing: pass` line, or not one `map:` line;
- the shared writing check fails;
- a confirmed.md line is not `- <Slot>: <value> | yes`;
- outcome's check_brief fails the mapped brief.

Check with me (exit 2, when the format is valid). Each item names the slot as the brief names it, the exact value, a
plain reason (Why) and a suggested answer (Suggest). The triggers are broad on purpose. A wrong item costs one yes:
- a Decided value, or a Parked `out of scope:` line with no question mark, that holds the word "unknown" anywhere, any
  question mark (`?`, `？`, `؟` and the rest), a hedge such as "maybe" or "not sure", a trap word such as "clean" or
  "good", a hole inside a longer value, a value check_brief would ask about such as `ok`, or `none`;
- a blank slot or line (also format invalid);
- an Open item with no question mark, or with a hole inside it;
- a Parked `out of scope:` line with a question mark: is it a limit or a question?
- a Parked line check_brief's judge() would ask about;
- every value check_brief asks about on the mapped brief, such as an Evals line with no pass case and fail case. A yes
  cannot clear that one: label the cases.

confirmed.md sits next to decisions.md, or at the path after `--confirmed`. Blank lines and `#` lines are skipped.
Each other line is one answer, the slot and the exact value from the list, then ` | yes`:

    - Output: file format (CSV/JSON): unknown | yes

A yes clears the item with that exact slot and value. It never clears a format error. A line that matches no item
is printed as a NOTE, not a failure. The mapper copies each yes into the brief's `## Confirmed` block.

Prints a PASS or FAIL line per check, the CHECK WITH ME list, any NOTE lines, then
`PASS|FORMAT INVALID|CHECK WITH ME decisions: <path>`. Exit 0 pass, 1 format invalid, 2 check with me, 3 usage: bad
arguments, or a path that is missing, a directory, or not UTF-8 text, with one line on stderr. A UTF-8 BOM is ignored.
"""
import contextlib
import io
import os
import re
import sys
import tempfile
import unicodedata
from collections import namedtuple

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared")))
from check_writing import check_writing  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outcome", "check")))
from check_brief import TRAP, check as check_brief, core, found_asks as brief_asks, judge  # noqa: E402

SECTIONS = ["Decided", "Open", "Parked", "Handoff"]
# Names are ASCII. re.A keeps IGNORECASE from matching a dotless i or a long s, so no lookup meets an unknown name.
NAMES = re.A | re.I
HEAD = re.compile(r"^##\s+(Decided|Open|Parked|Handoff)\s*$", NAMES)
BULLET = re.compile(r"^[-*]\s+(.*)$")
STOPS = {"done", "turn-cap", "open-cap"}
NEXT = "next: /automate-me:outcome"
TITLE = re.compile(r"^# Decisions\b", re.M)
MAX_TURNS = 10
OPEN_CAP = 5
SLOTS = ["goal", "done", "output", "verify", "constraints"]
# A slot label may have spaces before the colon, and the colon may be full-width.
SLOT_HEAD = re.compile(r"^(goal|done|output|verify|constraints)\s*[:：]\s*(.*)$", NAMES)
OUT_OF_SCOPE = re.compile(r"^[*_]*out of scope[*_]*\s*[:：][*_]*\s*", NAMES)
ASCII_DIGITS = re.compile(r"^[0-9]+$")
# A fence is ``` or ~~~, three or more, with optional info. A closer matches the
# innermost fence's character and length and has no info. Text inside any of them is hidden.
FENCE_LINE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HANDOFF_FIELD = re.compile(r"^(next|stop|turns|writing|map)\s*[:：]\s*(.*)$", NAMES)
# A tools:, agents:, evals:, decide: or write first: label. Bold, italics and a singular label still name that line.
EXTRA_HEAD = re.compile(r"^[*_]*(tools?|agents and roles|agents?|evals?|decide|write first)[*_]*\s*[:：][*_]*\s*(.*)$",
                        NAMES)
EXTRA_NAME = {"tool": "tools", "agent": "agents", "agents and roles": "agents", "eval": "evals"}
LOOSE_SLOT = re.compile(r"^(?:\d+[.)]\s*)?[*_]+\s*(goal|done|output|verify|constraints)\s*[*_]*\s*[:：]"
                        r"|^\d+[.)]\s*(goal|done|output|verify|constraints)\s*[:：]", NAMES)
BRIEF_SLOT = {"goal": "Goal", "done": "Done", "output": "Output", "verify": "Verification",
              "constraints": "Constraints", "tools": "Tools", "agents": "Agents and roles", "evals": "Evals",
              "decide": "Goal", "write first": "Tools"}
# A `stated:` label. Markup before it with none after it wraps the whole value, so that markup stays around the rest.
# Markup closes the label only when it touches the colon, so `stated: *unknown*` keeps both stars.
STATED = re.compile(r"^([*_`]*)\s*stated\s*([*_`]*)\s*[:：]([*_]*)\s*", NAMES)
# A brief tag that may lead a line. unstated() keeps it and drops any `stated:` beside it.
TAG_LABEL = re.compile(r"^[*_]*(?:investigate|out of scope|how|write first)[*_]*\s*[:：][*_]*\s*", NAMES)
CONFIRMED_LINE = re.compile(r"^[-*]\s+(?P<slot>[^:]+?)\s*:\s(?P<value>.*\S)\s+\|\s*(?P<answer>[^|]*?)\s*$")
HEDGES = re.compile(r"(?<![^\W_])(?:maybe|perhaps|possibly|probably|might|unsure|unclear|not sure|i think|i guess"
                    r"|for now|depends|idk|dunno|tbh)(?![^\W_])")
TRAPS = re.compile(r"(?<![^\W_])(?:" + "|".join(sorted(TRAP)) + r")(?![^\W_])")
BRIEF_CHECK = "the mapped brief passes outcome's brief check"
EVALS_ASK = "ASK: Evals: Is there a pass case and a fail case here?"

Item = namedtuple("Item", "slot value why suggest clears")


def canon(name):
    """The section an ASCII heading names."""
    return next((s for s in SECTIONS if s.lower() == name.lower()), None)


def is_none(item):
    return item.strip().rstrip(".").lower() == "none"


def real_items(items):
    """A lone `none` means the section is empty."""
    if len(items) == 1 and is_none(items[0]):
        return []
    return items


def split_fences(text):
    """Returns (visible, hidden, unclosed, fenced). Fence markers themselves are dropped.

    ``` and ~~~ both count, at any length of 3 or more. A fence inside a fence
    is nested: it hides its own text and does not close the outer fence unless
    it is the same character, the same length, and has no info string.
    Hidden prose is still returned so the writing check can see it.
    fenced lists the section each outer fence opened in, or None before the first section.
    """
    visible, hidden, stack, fenced = [], [], [], []
    section = None
    for line in text.splitlines():
        match = FENCE_LINE.match(line)
        if match:
            mark = match.group(2)
            char, length, info = mark[0], len(mark), match.group(3).strip()
            if stack and char == stack[-1][0] and length == stack[-1][1] and info == "":
                stack.pop()
            else:
                if not stack:
                    fenced.append(section)
                stack.append((char, length))
            continue
        if not stack:
            head = HEAD.match(line.strip())
            if head:
                section = canon(head.group(1))
        (hidden if stack else visible).append(line)
    return "\n".join(visible), "\n".join(hidden), bool(stack), fenced


def unstated(value):
    """The value with every `stated:` label among its leading labels gone, bold or not. A tag such as `how:` stays.

    Markup is kept. A code span after the label keeps both backticks, and a label inside a code span leaves the span
    around the rest.
    """
    text, tags = (value or "").strip(), ""
    while True:
        label = STATED.match(text)
        tag = TAG_LABEL.match(text)
        if label:
            wrap = "" if label.group(2) or label.group(3) else label.group(1)
            text = (wrap + text[label.end():]).strip()
        elif tag:
            tags, text = tags + tag.group(), text[tag.end():]
        else:
            return (tags + text).strip()


def blank(value):
    """True when nothing is left once markup, punctuation and one leading tag go, as check_brief's core() reads it."""
    return not core(value or "")


def has_question(text):
    """True when any character is a question mark of any script: `?`, `？`, `؟`, `;`, `⁇`, `¿` and the rest."""
    return any("QUESTION" in unicodedata.name(char, "") for char in text or "")


def open_body(item):
    """An Open item's question without its slot or line label and without leading `unknown:` or `stated:`."""
    extra = extra_of(item)
    text = slot_value(item) if slot_of(item) else extra[1] if extra else item
    return re.sub(r"^(?:\s*(?:unknown|stated)\s*:)+", "", text, flags=re.I).strip()


def open_slot(item):
    """The brief slot an Open item fills: its slot, or Unknowns."""
    return BRIEF_SLOT[slot_of(item)] if slot_of(item) else "Unknowns"


def scoped(item):
    """An `out of scope:` line, bold or not, as the brief writes it in Constraints."""
    return "out of scope: " + unstated(OUT_OF_SCOPE.sub("", item.strip(), count=1))


def extra_of(item):
    """(name, value) when the line is tools:, agents: (or agents and roles:), evals:, decide:, or write first:."""
    match = EXTRA_HEAD.match(item.strip())
    if not match:
        return None
    name = match.group(1).lower()
    return EXTRA_NAME.get(name, name), match.group(2).strip()


def parked_limit(row):
    """A Parked `out of scope:` line with no question mark. The brief puts it in Constraints."""
    return bool(OUT_OF_SCOPE.match(row.strip())) and not has_question(row)


def parked_value(row):
    """A Parked line as the brief writes it."""
    return scoped(row) if OUT_OF_SCOPE.match(row.strip()) else unstated(row)


def parse(text):
    """Returns (sections, counts, positions, extras).

    sections maps a label to its bullet items. extras are non-bullet lines inside a section,
    which means an item ran past one line.
    """
    sections, counts, positions, extras = {}, {}, [], []
    current = None
    for raw in text.splitlines():
        line = raw.rstrip()
        head = HEAD.match(line.strip())
        if head:
            current = canon(head.group(1))
            counts[current] = counts.get(current, 0) + 1
            sections.setdefault(current, [])
            positions.append(current)
            continue
        if current is None or not line.strip():
            continue
        bullet = BULLET.match(line)
        if bullet:
            sections[current].append(bullet.group(1).strip())
        else:
            extras.append((current, line.strip()))
    return sections, counts, positions, extras


def slot_match(item):
    return SLOT_HEAD.match(item.strip())


def slot_value(item):
    """The text after the slot colon, else None. Spaces and a full-width colon count."""
    match = slot_match(item)
    return match.group(2).strip() if match else None


def slot_of(item):
    match = slot_match(item)
    return match.group(1).lower() if match else None


def is_slot_line(item):
    return slot_of(item) is not None


def has_slot(items, slot):
    return any(slot_of(item) == slot for item in items)


def handoff_fields(items):
    """Handoff fields, with bold markers stripped and the label case-folded.

    `**stop:** open-cap` is a stop field. `writing: PASS` is `pass`.
    """
    found = {name: [] for name in ("next", "stop", "turns", "writing", "map")}
    for item in items:
        plain = item.replace("**", "").strip()
        plain = re.sub(r"^[\*_]+|[\*_]+$", "", plain).strip()
        match = HANDOFF_FIELD.match(plain)
        if match:
            found[match.group(1).lower()].append(match.group(2).strip())
    return found


def prose_fails(text):
    """Runs the shared writing check. A self-reported writing line is not consulted."""
    handle = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
    try:
        handle.write(text)
        handle.close()
        with contextlib.redirect_stdout(io.StringIO()):
            return check_writing(handle.name)
    finally:
        os.remove(handle.name)


def landing(item):
    """(brief slot, value, label) for one Decided line, as the mapper places it. The value has no `stated:` label.

    label is the slot or line label (goal, tools, write first, out of scope, ...), or None for any
    other line, which lands in Done. A `decide:` value is the Goal's decide item, with no prefix.
    """
    slot = slot_of(item)
    if slot:
        return BRIEF_SLOT[slot], unstated(slot_value(item)), slot
    extra = extra_of(item)
    if extra:
        return BRIEF_SLOT[extra[0]], unstated(extra[1]), extra[0]
    if OUT_OF_SCOPE.match(item.strip()):
        return "Constraints", scoped(item), "out of scope"
    return "Done", unstated(item), None


def answers(decided, parked):
    """(brief slot, value) for every answer the brief will hold: each Decided value, and each Parked `out of scope:`
    line with no question mark, which the mapper puts in Constraints."""
    return ([(slot, value) for slot, value, _ in map(landing, decided)]
            + [("Constraints", scoped(row)) for row in parked if parked_limit(row)])


def sections_of(text):
    visible = split_fences(text.lstrip("﻿"))[0]
    sections = parse(visible)[0]
    return {name: real_items(sections.get(name, [])) for name in SECTIONS}


def check(text):
    """[(check name, fails)] for the format. Every fail here is certain. See the module docstring."""
    visible, hidden, unclosed, fenced = split_fences(text.lstrip("﻿"))
    sections, counts, positions, extras = parse(visible)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("code fence is closed", [] if not unclosed else ["a code fence is opened and never closed"])
    add("no code fence under Decided, Open or Parked",
        [f"a code fence under {section} is not read, so its text would be lost. Put that text on the item's own line"
         for section in fenced if section in ("Decided", "Open", "Parked")])
    add("file has a Decisions title", [] if TITLE.search(visible) else ["missing a `# Decisions` title"])

    present = []
    for name in SECTIONS:
        n = counts.get(name, 0)
        if n == 0:
            present.append(f"missing section: {name}. Write the heading `## {name}` with plain ASCII letters")
        elif n != 1:
            present.append(f"section {name} appears {n} times")
    add("sections present once", present)

    order = []
    if all(counts.get(name) == 1 for name in SECTIONS) and positions != SECTIONS:
        order.append("sections are " + ", ".join(positions) + "; use Decided, Open, Parked, Handoff")
    add("sections in order", order)

    decided = real_items(sections.get("Decided", []))
    opens = real_items(sections.get("Open", []))
    parked = real_items(sections.get("Parked", []))
    add("no open item is a placeholder",
        [f"open item {item!r} is only a placeholder or a template hole, not a question" for item in opens
         if not (slot_of(item) and blank(open_body(item))) and judge(open_body(item))[0] == "fail"])
    loose = {}
    for line in decided + opens + [text for name, text in extras if name in ("Decided", "Open")]:
        match = LOOSE_SLOT.match(line)
        if match:
            loose.setdefault((match.group(1) or match.group(2)).lower(), line)
    missing = []
    for slot in SLOTS:
        if has_slot(decided, slot) or has_slot(opens, slot):
            continue
        if slot in loose:
            missing.append(f"slot {slot} is written as {loose[slot]!r}. Write `- {slot}: ...` with no bold or number")
        else:
            missing.append(f"missing slot: {slot}. Add a Decided `{slot}:` line or an Open `{slot}: ...?` item")
    add("every slot is decided or open", missing)

    dup_fails, both_fails, empty_fails = [], [], []
    for slot in SLOTS:
        in_decided = [item for item in decided if slot_of(item) == slot]
        in_open = [item for item in opens if slot_of(item) == slot]
        if len(in_decided) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_decided)} Decided lines")
        if len(in_open) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_open)} Open lines")
        if in_decided and in_open:
            both_fails.append(f"slot {slot} is both Decided and Open")
        empty_fails += [f"slot {slot} has an empty value: {item!r}" for item in in_decided
                        if blank(unstated(slot_value(item)))]
        empty_fails += [f"slot {slot} has an empty value: {item!r}" for item in in_open if blank(open_body(item))]
    add("no duplicate slot", dup_fails)
    add("a slot is not in Decided and Open", both_fails)
    add("slot values are not empty", empty_fails)

    extra_fails, seen_extra = [], set()
    for name, value in filter(None, map(extra_of, decided)):
        if name in seen_extra:
            extra_fails.append(f"{name}: is on more than one Decided line")
        seen_extra.add(name)
        if blank(unstated(value)):
            extra_fails.append(f"{name}: needs a value")
    add("tools, agents, evals, and decide lines are usable", extra_fails)

    # A Parked line is blank when nothing is left as written, or once a slot or line label goes (`decide: stated:`).
    empty = [("Decided", row) for row in decided if not slot_of(row) and not extra_of(row) and blank(landing(row)[1])]
    empty += [("Parked", row) for row in parked if blank(parked_value(row)) or blank(landing(row)[1])]
    add("every line has a value", [f"{source} line {row!r} has no value once its labels are gone; write the value or"
                                   " drop the line" for source, row in empty])
    values = answers(decided, parked)
    values += [("Parking lot", parked_value(row)) for row in parked if not is_none(row) and not parked_limit(row)]
    add("no value is a placeholder or template text",
        [f"{slot}: {value!r} is a placeholder or template text; write the real answer" for slot, value in values
         if not blank(value) and core(value) != "none" and judge(value)[0] == "fail"])

    handoff = sections.get("Handoff", [])
    handoff_ready = counts.get("Handoff") == 1
    fields = handoff_fields(handoff) if handoff_ready else {name: [] for name in ("next", "stop", "turns", "writing", "map")}
    stops = [value.lower() for value in fields["stop"]]
    unique_fails = []
    if len(fields["next"]) > 1:
        unique_fails.append(f"next appears {len(fields['next'])} times")
    if len(set(stops)) > 1:
        unique_fails.append("stop lines disagree: " + ", ".join(stops))
    if len(fields["turns"]) > 1:
        unique_fails.append(f"turns appears {len(fields['turns'])} times")
    if len({value.lower() for value in fields["writing"]}) > 1:
        unique_fails.append("writing lines disagree")
    add("handoff fields are unique", unique_fails)

    stop_fails = []
    if handoff_ready and len(stops) == 0:
        stop_fails.append("stop line is missing; write stop: done, stop: turn-cap, or stop: open-cap")
    elif len(stops) > 1 and len(set(stops)) == 1:
        stop_fails.append(f"stop appears {len(stops)} times")
    elif stops and stops[0] not in STOPS:
        stop_fails.append(f"stop is {stops[0]!r}; use done, turn-cap, or open-cap")
    add("stop reason is done, turn-cap, or open-cap", stop_fails)

    turns = fields["turns"]
    turn_fails = []
    turn_number = None
    if handoff_ready and len(turns) == 0:
        turn_fails.append("turn count is missing; write turns: <n> in Handoff")
    elif len(turns) > 1:
        turn_fails.append(f"turn count appears {len(turns)} times")
    elif turns and (len(turns[0]) > 2 or not ASCII_DIGITS.fullmatch(turns[0])):
        shown = turns[0] if len(turns[0]) <= 20 else turns[0][:20] + "..."
        turn_fails.append(f"turns is {shown!r}; write a whole number from 1 through {MAX_TURNS}")
    elif turns:
        turn_number = int(turns[0])
        if turn_number < 1 or turn_number > MAX_TURNS:
            turn_fails.append(f"turns is {turn_number}, write a whole number from 1 through {MAX_TURNS}")
    add("turn count recorded and at most 10", turn_fails)

    stop = stops[0] if len(stops) == 1 and stops[0] in STOPS else None
    non_slot = [item for item in opens if not is_slot_line(item)]
    done_applies = all(has_slot(decided, slot) and not has_slot(opens, slot) for slot in SLOTS)
    open_cap_applies = turn_number is not None and turn_number >= 2 and len(non_slot) > OPEN_CAP
    if done_applies:
        first = "done"
    elif open_cap_applies:
        first = "open-cap"
    elif turn_number == MAX_TURNS:
        first = "turn-cap"
    else:
        first = None
    match_fails = []
    if stop == "done":
        for slot in SLOTS:
            if not has_slot(decided, slot):
                match_fails.append(f"stop is done but {slot} is not a Decided line")
            elif has_slot(opens, slot):
                match_fails.append(f"stop is done but {slot} is still Open")
    elif stop == "open-cap":
        if turn_number == 1:
            match_fails.append("open-cap is not valid on turn 1")
        if len(non_slot) <= OPEN_CAP:
            match_fails.append(
                f"open-cap needs more than {OPEN_CAP} open items that are not the five slots, found {len(non_slot)}")
    elif stop == "turn-cap" and turn_number != MAX_TURNS:
        match_fails.append(f"turn-cap needs turns: {MAX_TURNS}")
    add("stop matches the file", match_fails)
    add("stop is the first match", [f"stop is {stop} but the first match is {first}"] if first and stop and stop != first
        else [])
    add("turn 1 parks overflow",
        [f"turn 1 has {len(non_slot)} open items that are not slots; park the ones past {OPEN_CAP}"]
        if turn_number == 1 and len(non_slot) > OPEN_CAP else [])

    add("no item longer than one line",
        [f"{name}: extra line {text!r}. Each item stays on one line" for name, text in extras])

    nexts = [value.strip() for value in fields["next"]]
    add("handoff names outcome",
        [f"Handoff next is {nexts!r}; write one `{NEXT}` line"] if handoff_ready and nexts != ["/automate-me:outcome"]
        else [])
    add("handoff has a map line",
        ["Handoff needs one map: line, as the template shows"] if handoff_ready and len(fields["map"]) != 1 else [])
    writing = [value.lower() for value in fields["writing"]]
    add("handoff says writing pass",
        ["Handoff has no single `writing: pass` line. Run the shared writing check first"]
        if handoff_ready and writing != ["pass"] else [])
    add("prose passes the writing check", prose_fails(visible if not hidden else visible + "\n" + hidden))
    if not any(fails for _, fails in results):
        add(BRIEF_CHECK, [fail for _, fails in check_brief(mapped(text)) for fail in fails])
    return results


def mapped(text, confirmed=()):
    """The brief the mapper writes. map_decisions imports this module, so it is loaded on first use."""
    import map_decisions

    return map_decisions.map_text(text, confirmed)


# A value trigger: (test, why, suggest). test returns the word it found, or None. The first match names the item.
VALUE_TRIGGERS = [
    (lambda value: "none" if core(value) == "none" else None,
     'It says "none", so this slot may not be filled in yet.',
     "Confirm there is nothing for it, or write the real answer."),
    (lambda value: "unknown" if "unknown" in core(value) else None,
     'It says "unknown", so this may not be decided yet.',
     "Move it to Open as a question, or confirm it as is."),
    (lambda value: "?" if has_question(value) else None,
     "It has a question mark, so it may be a question and not a decision.",
     "Move it to Open if it is still a question, or confirm it as is if the answer quotes a question."),
    (lambda value: (HEDGES.search(core(value)) or [None])[0],
     'It says "{word}", so the person may not have decided.',
     "Ask for a firm answer and write that, move it to Open as a question, or confirm it as is."),
    (lambda value: (TRAPS.search(core(value)) or [None])[0],
     'The word "{word}" can mean many things, so nobody can check it.',
     "Name something a person can see or count, or confirm it as is."),
]
HOLE = ("It has text in angle or curly brackets, which may be a template hole.",
        "Fill in the real text, or confirm it as is if the brackets are meant.")
VAGUE = ("It is very short or vague, so it may not be a real answer.",
         "Write the full answer in the person's words, or confirm it as is.")
BLANK = ("It has no value.", "Ask the person for the {slot} and write it here, or move it to Open as a question.")
NO_QUESTION = ("It sits in Open but has no question mark, so it may be a decision.",
               "Make it a question that ends in a question mark, or move it to Decided if it is settled.")
LIMIT_OR_QUESTION = ("It is tagged out of scope and also has a question mark, so it may be a question and not a limit.",
                     "Confirm it to keep it as a question for later, or drop the question mark if it is a firm limit.")
BRIEF_ASK = ("Outcome's brief check is not sure this is a real answer.", "Write the full answer, or confirm it as is.")
EVALS_CASES = ("Evals needs one case that should pass and one that should fail, and the check cannot find both.",
               "Label each case, as `pass: <case>; fail: <case>`. A yes does not clear this one.")


def judged(slot, value):
    """The Item check_brief's judge() asks for, or None."""
    outcome, why = judge(value)
    if outcome != "ask":
        return None
    return Item(slot, value, *(HOLE if why == "hole" else VAGUE), True)


def value_item(slot, value):
    """The Item for one answer, or None."""
    if blank(value):
        return Item(slot, value, BLANK[0], BLANK[1].format(slot=slot.lower()), True)
    for test, why, suggest in VALUE_TRIGGERS:
        word = test(value)
        if word:
            return Item(slot, value, why.format(word=word), suggest, True)
    return judged(slot, value)


def review(text, with_brief=True):
    """Every CHECK WITH ME Item, before confirmations, in file order, one per slot and value.

    with_brief adds the values check_brief asks about on the mapped brief. Run it only when the format is valid.
    """
    found = sections_of(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    out = [value_item(slot, value) for slot, value in answers(decided, parked)]
    for item in opens:
        body = open_body(item)
        if slot_of(item) and blank(body):
            out.append(Item(open_slot(item), body, BLANK[0], BLANK[1].format(slot=open_slot(item).lower()), True))
        elif not has_question(item):
            out.append(Item(open_slot(item), body, *NO_QUESTION, True))
        else:
            out.append(judged(open_slot(item), body))
    for row in parked:
        if OUT_OF_SCOPE.match(row.strip()) and has_question(row):
            out.append(Item("Parking lot", parked_value(row), *LIMIT_OR_QUESTION, True))
        elif not parked_limit(row) and not blank(parked_value(row)):
            out.append(judged("Parking lot", parked_value(row)))
    if with_brief:
        for slot, value, line in brief_asks(mapped(text)):
            out.append(Item(slot, value, *(EVALS_CASES if line == EVALS_ASK else BRIEF_ASK), line != EVALS_ASK))
    seen, unique = set(), []
    for item in filter(None, out):
        if (item.slot, item.value) not in seen:
            seen.add((item.slot, item.value))
            unique.append(item)
    return unique


def read_confirmed(text):
    """([(slot, value)] for each yes, [fails]) from confirmed.md text."""
    yes, fails = [], []
    for raw in (text or "").lstrip("﻿").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = CONFIRMED_LINE.match(line)
        if not match:
            fails.append(f"confirmed.md line {line!r} is not `- <Slot>: <value> | yes`")
        elif match["answer"].lower() != "yes":
            fails.append(f"confirmed.md line {line!r} answers {match['answer']!r}. Only yes confirms a value. "
                         "For any other answer, edit decisions.md")
        else:
            yes.append((match["slot"].strip(), match["value"].strip()))
    return yes, fails


Verdict = namedtuple("Verdict", "code results pending notes used")


def verdict(text, confirmed_text=""):
    """The one result both scripts print. code is 0 pass, 1 format invalid, 2 check with me."""
    yes, confirm_fails = read_confirmed(confirmed_text)
    results = check(text) + [("confirmed.md lines are `- <Slot>: <value> | yes`", confirm_fails)]
    failed = any(fails for _, fails in results)
    found = review(text, with_brief=not failed)
    keys = {(item.slot, item.value) for item in found}
    pending = [item for item in found if not (item.clears and (item.slot, item.value) in yes)]
    used = [key for key in dict.fromkeys(yes) if key in keys]
    notes = [f"NOTE: confirmed.md line '- {slot}: {value} | yes' matches nothing in decisions.md now; remove it"
             for slot, value in dict.fromkeys(yes) if (slot, value) not in keys]
    if not failed and not pending:
        # The brief must pass check_brief whole. Anything it still asks about stays on the list.
        pending = [Item(slot, value, *(EVALS_CASES if line == EVALS_ASK else BRIEF_ASK), False)
                   for slot, value, line in brief_asks(mapped(text, used))]
    code = 1 if failed else 2 if pending else 0
    return Verdict(code, results, pending, notes, used)


def report(text, path, confirmed_text=""):
    """(exit code, printed lines, Verdict)."""
    result = verdict(text, confirmed_text)
    lines = []
    for name, fails in result.results:
        lines.append(f"{'FAIL' if fails else 'PASS'} {name}")
        lines += [f"  {fail}" for fail in fails]
    if result.pending:
        lines.append(f"CHECK WITH ME ({len(result.pending)})")
        for item in result.pending:
            lines += [f'- {item.slot}: "{item.value}"', f"  Why: {item.why}", f"  Suggest: {item.suggest}"]
    lines += result.notes
    lines.append(f"{['PASS', 'FORMAT INVALID', 'CHECK WITH ME'][result.code]} decisions: {path}")
    return result.code, lines, result


def read(path):
    """(text without a BOM, None), or (None, why) when the path cannot be read as UTF-8 text."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            return handle.read(), None
    except UnicodeDecodeError:
        return None, "not UTF-8 text"
    except OSError as err:
        return None, err.strerror or str(err)


def unreadable(path, why):
    """Prints the one usage line for a path that cannot be read, and returns exit 3."""
    print(f"usage: cannot read {path}: {why}", file=sys.stderr)
    return 3


def inputs(path, confirmed=None):
    """(decisions text, confirmed.md text, None), or (None, None, exit 3) after one usage line on stderr.

    Without --confirmed, confirmed.md next to decisions.md is read when it exists.
    """
    text, why = read(path)
    if why:
        return None, None, unreadable(path, why)
    beside = os.path.join(os.path.dirname(os.path.abspath(path)), "confirmed.md")
    if confirmed is None and not os.path.isfile(beside):
        return text, "", None
    confirmed = confirmed or beside
    answers_text, why = read(confirmed)
    if why:
        return None, None, unreadable(confirmed, why)
    return text, answers_text, None


def arguments(argv, usage):
    """(decisions path, confirmed path or None), or None after one usage line on stderr."""
    if len(argv) == 1:
        return argv[0], None
    if len(argv) == 3 and argv[1] == "--confirmed":
        return argv[0], argv[2]
    if len(argv) == 3 and argv[0] == "--confirmed":
        return argv[2], argv[1]
    print(usage, file=sys.stderr)
    return None


def main(path, confirmed=None):
    text, answers_text, code = inputs(path, confirmed)
    if code:
        return code
    code, lines, _ = report(text, path, answers_text)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__.strip())
        sys.exit(0)
    args = arguments(sys.argv[1:], "usage: python3 check/check_decisions.py <decisions.md> [--confirmed <confirmed.md>]")
    sys.exit(3 if args is None else main(*args))
