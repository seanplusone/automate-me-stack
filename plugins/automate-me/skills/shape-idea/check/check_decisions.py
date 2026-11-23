"""Checks a decisions.md written by the shape-idea skill.

Usage: python3 check/check_decisions.py <decisions.md> [--confirmed <confirmed.md>]

There are three outcomes.

1. FORMAT INVALID, exit 1. Only what the script knows for certain (see "Format invalid" below).
2. CHECK WITH ME, exit 2, when the format is valid. One list of values the script cannot be sure about. The agent
   asks the person about each item and records each answer, a yes or a new answer, in confirmed.md.
3. PASS, exit 0, when the format is valid and every item on the list has an answer that clears it.

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
- a value is untouched template text: a template hole such as `<goal>`, a line of the template left unfilled, or
  only words from outcome's fixed placeholder list such as TBD, TODO or N/A (check_brief's judge() says fail). `none`
  is not on this list here: it is on the CHECK WITH ME list. An `[insert ...]` inside a longer value, a placeholder
  word beside other words, or a placeholder in a code span is not untouched: it is on the CHECK WITH ME list;
- an Open item is only a placeholder or only a hole (`TBD?`, `?`, `<question>?`);
- stop is missing, repeated, not one of done, turn-cap, open-cap, or does not match the file;
- turns is missing, repeated, or not a whole number from 1 through 10;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line, no single `writing: pass` line, or not one `map:` line;
- the shared writing check fails;
- a confirmed.md line is not `- <Slot>: <value> | <answer>`, or its answer is `no` alone;
- outcome's check_brief fails the mapped brief, or still asks about a value once every item is answered.

One shared check. Every value goes through judge_value(slot, text, role), which returns Verdict(error, piece, item):
the format error the script is sure of, and the item to check with the person. entries() only finds the values, and
the slot only picks the wording and the Ask questions, so the same text gets the same verdict in every slot. It reads
a value in three layers:
- text checks, everywhere: blank or untouched (format invalid); `none`; a word from outcome's fixed placeholder list
  inside a longer value, even when punctuation joins it (`a card/TBD`, `poster-TBD`); an `[insert ...]` or a hole
  inside a longer value; a value check_brief would ask about, such as `ok`. A code span is literal text, so
  `` `N/A` `` is listed, not format invalid;
- decision checks, on a Decided value and an `out of scope:` line: the word "unknown" anywhere, any question mark (`?`,
  `？`, `؟` and the rest), a hedge such as "maybe" or "not sure", a trap word such as "clean" or "good";
- the question check, on an Open line: it is a question when it ends in a question mark of any script, once closing
  markup, quotes and brackets go. A mark only in the middle is listed.
A Parked line is for later, so only the text checks apply. A Parked `out of scope:` line with a question mark may be a
limit or a question. An Evals answer is read in pieces as check_brief reads it, the text before the first colon label
and each case body of either form. A should pass or should fail phrase with nothing before it is not a case, and the
text after a phrase that no case body holds is read with that phrase. When its pass case or fail case is missing, that
is the one item for the line, and a yes cannot clear it, so the brief check reads the brief without that line.

Check with me (exit 2, when the format is valid). Each item names the slot as the brief names it and the exact value,
then four lines. Why is one short plain sentence that quotes at most a short piece of the value. Ask holds one to
three questions for that slot that narrow the answer. Suggest is a next step, and says "confirm it as is" only when a
yes can clear the item. Line is the item's confirmed.md line, ready to copy, with `yes` or `<new answer>` after the
bar. A value whose own line has a format error has no Line, because no answer clears it. The triggers are broad on
purpose. A wrong item costs one answer.

confirmed.md sits next to decisions.md, or at the path after `--confirmed`. Blank lines and `#` lines are skipped.
Each other line is one answer, the slot and the exact value from the list, a bar, then `yes` or a new answer:

    - Output: maybe a poster on the gym door | yes
    - Output: maybe a poster on the gym door | a poster on the gym door

A yes clears the item with that exact slot and value, and no other: `tools: X` and `agents: X` are two items. A new
answer takes the old value's place on every line with that slot and value, label kept once, and goes through the same
shared check, so an answer that is still unsure is listed again under its new text. A bar inside the value or the
answer is written `\\|`, and a backslash `\\\\`, so the one unescaped bar ends the value: in `\\\\|` the bar is
unescaped. A line with no such bar, or with two, is format invalid. The latest line for the same slot and value wins.
Lines apply in confirmed.md order, and a yes clears a value only if the value is there when the yes applies.

The format checks read decisions.md as written, before any new answer is put in, and again with the new answers in
place. So no answer clears a format error, a writing failure included, and a new answer can add one. A line naming a
value with a format error prints a NOTE. A line that matches nothing is printed as a NOTE, not a failure.
decisions.md is not changed: the mapper maps it with the new answers in place, and copies each yes into the brief's
`## Confirmed` block.

Prints a PASS or FAIL line per check, the CHECK WITH ME list, any NOTE lines, then
`PASS|FORMAT INVALID|CHECK WITH ME decisions: <path>`. Exit 0 pass, 1 format invalid, 2 check with me, 3 usage: bad
arguments, or a path that is missing, a directory, or not UTF-8 text, with one line on stderr. A UTF-8 BOM is ignored.
Files are read and written as UTF-8, and output is UTF-8, whatever the locale.
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
from check_brief import (  # noqa: E402
    INSERT_FINDER,
    PLACEHOLDER,
    TEMPLATE,
    TRAP,
    case_marks,
    check as check_brief,
    core,
    eval_cases,
    eval_lead,
    found,
    found_asks as brief_asks,
    judge,
)

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
# A confirmed.md line. The one unescaped bar ends the value. See bar() and unbar().
CONFIRMED_LINE = re.compile(r"^[-*]\s+(?P<slot>[^:]+?)\s*:\s(?P<rest>.*)$")
# In confirmed.md, \| is a bar and \\ is a backslash. Any other backslash is itself.
BAR_TOKEN = re.compile(r"\\[\\|]|\||[^\\|]+|\\")
HEDGES = re.compile(r"(?<![^\W_])(?:maybe|perhaps|possibly|probably|might|unsure|unclear|not sure|i think|i guess"
                    r"|for now|depends|idk|dunno|tbh)(?![^\W_])")
TRAPS = re.compile(r"(?<![^\W_])(?:" + "|".join(sorted(TRAP)) + r")(?![^\W_])")
BRIEF_CHECK = "the mapped brief passes outcome's brief check"
CONFIRMED_CHECK = "confirmed.md lines are `- <Slot>: <value> | <answer>`"
# The words of outcome's fixed placeholder list that are also everyday words. Only placeholder_in() reads this.
EVERYDAY = {"none", "later", "pending", "placeholder"}

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


def insert_in(value):
    """The first `[insert ...]` outside code in a value that has other words, or None. Alone it is a template hole."""
    if not found(INSERT_FINDER, value) or untouched(value):
        return None
    return next(m.group() for m in INSERT_FINDER.finditer(value) if m.group("keep") is None)


def untouched(value):
    """True when the value is nothing but template text, holes or placeholders, so check_brief's judge() fails it whole.

    A code span is the person's literal text, so `` `N/A` `` is not untouched. An `[insert ...]` inside a longer value
    may be literal text too, as `show the prompt [Insert card]`, so it is not untouched when the rest passes.
    """
    if judge(value)[0] != "fail" or core(value) == "none":
        return False
    rest = INSERT_FINDER.sub(lambda m: " literal " if m.group("keep") else " ", value)
    return core(value) in TEMPLATE or judge(rest)[0] == "fail"


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


def open_key(item):
    """(brief slot, value) a confirmation names for an Open item, as the mapper places it.

    A slot or a `tools:`, `agents:` or `evals:` question fills that brief slot, so two labels with the same text are two
    items. Any other item goes to Unknowns, and a `decide:` or `write first:` label stays on its value there.
    """
    if slot_of(item):
        return BRIEF_SLOT[slot_of(item)], open_body(item)
    extra = extra_of(item)
    if extra and extra[0] in ("tools", "agents", "evals"):
        return BRIEF_SLOT[extra[0]], open_body(item)
    return "Unknowns", f"{extra[0]}: {open_body(item)}" if extra else open_body(item)


LIMIT = "out of scope: "


def scoped(item):
    """An `out of scope:` line, bold or not, as the brief writes it in Constraints."""
    return LIMIT + unstated(OUT_OF_SCOPE.sub("", item.strip(), count=1))


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
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False)
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
    # Every value goes through the one shared check. The checks below only group its format errors by where they sit.
    judged = [(entry, *judge_value(entry.slot, entry.text, entry.role)[:2])
              for entry in entries({"Decided": decided, "Open": opens, "Parked": parked})]
    add("no open item is a placeholder",
        [f"open item {entry.row!r} is only a placeholder or a template hole, not a question" for entry, error, _ in judged
         if error and entry.section == "Open" and (error == "placeholder" or entry.kind != "slot")])
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

    dup_fails, both_fails = [], []
    for slot in SLOTS:
        in_decided = [item for item in decided if slot_of(item) == slot]
        in_open = [item for item in opens if slot_of(item) == slot]
        if len(in_decided) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_decided)} Decided lines")
        if len(in_open) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_open)} Open lines")
        if in_decided and in_open:
            both_fails.append(f"slot {slot} is both Decided and Open")
    add("no duplicate slot", dup_fails)
    add("a slot is not in Decided and Open", both_fails)
    add("slot values are not empty", [f"slot {entry.label[:-2]} has an empty value: {entry.row!r}"
                                      for entry, error, _ in judged if error == "blank" and entry.kind == "slot"])

    extra_fails, seen_extra = [], set()
    for name, _ in filter(None, map(extra_of, decided)):
        if name in seen_extra:
            extra_fails.append(f"{name}: is on more than one Decided line")
        seen_extra.add(name)
    extra_fails += [f"{entry.label[:-2]}: needs a value" for entry, error, _ in judged
                    if error == "blank" and entry.kind == "extra"]
    add("tools, agents, evals, and decide lines are usable", extra_fails)

    add("every line has a value", [f"{entry.section} line {entry.row!r} has no value once its labels are gone; write"
                                   " the value or drop the line" for entry, error, _ in judged
                                   if error == "blank" and entry.kind == "line" and entry.section != "Open"])
    add("no value is a placeholder or template text",
        [f"{entry.slot}: {entry.value!r} is a placeholder or template text; write the real answer" if piece == entry.text
         else f"{entry.slot}: {entry.value!r} has a case {piece.strip(' ;,.')!r} that is a placeholder or template text;"
         " write the real case" for entry, error, piece in judged if error == "placeholder" and entry.section != "Open"])

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


def placeholder_in(value):
    """The first word or phrase of outcome's fixed placeholder list inside a value, as written, or None.

    A value made only of placeholders is format invalid. This finds one inside a longer value, as `TBD by Friday`, and
    one joined to a word by any punctuation, as `a card/TBD` or `poster-TBD`. A word of that list that is also an
    everyday word, such as `later` in `a watch app later`, is that word inside a longer value.
    """
    for match in PLACEHOLDER.finditer(core(value)):
        if match.group() in EVERYDAY:
            continue
        spelled = re.search(r"[\W_]+".join(map(re.escape, re.split(r"[\W_]+", match.group()))), value, re.I)
        return spelled.group() if spelled else match.group()
    return None


def ends_in_question(text):
    """True when the text ends in a question mark of any script once closing markup, quotes, brackets and spaces go."""
    rest = (text or "").rstrip()
    while rest and (rest[-1] in "*_~`'\"" or unicodedata.category(rest[-1]) in ("Pe", "Pf") or rest[-1].isspace()):
        rest = rest[:-1]
    return has_question(rest[-1:])


def quoted(piece, fallback):
    """The piece in a code span when it is short plain text, else fallback, so a Why never echoes a long value or an
    odd character. The writing check skips a code span, so a word from the value never fails it."""
    return f"`{piece}`" if len(piece) <= 30 and re.fullmatch(r"[A-Za-z0-9 /.,()\[\]-]+", piece) else fallback


# Where a value sits. An answer is a decision, so a word that says it is not decided is listed. A question is an Open
# line. A note is a Parked line, which is for later, so a hedge there is fine. The text checks apply to all three.
ANSWER, QUESTION, NOTE = "answer", "question", "note"
EVERY = (ANSWER, QUESTION, NOTE)
# (reason, test, roles). test returns the word it found, or None. The first match names the item.
TRIGGERS = [
    ("no question", lambda text: None if ends_in_question(text) else "?", (QUESTION,)),
    ("none", lambda text: "none" if core(text) == "none" else None, EVERY),
    ("placeholder", placeholder_in, EVERY),
    ("unknown", lambda text: "unknown" if "unknown" in core(text) else None, (ANSWER,)),
    ("question", lambda text: "?" if has_question(text) else None, (ANSWER,)),
    ("hedge", lambda text: (HEDGES.search(core(text)) or [None])[0], (ANSWER,)),
    ("trap", lambda text: (TRAPS.search(core(text)) or [None])[0], (ANSWER,)),
    ("insert", insert_in, EVERY),
    ("hole", lambda text: "hole" if judge(text) == ("ask", "hole") else None, EVERY),
    ("vague", lambda text: "vague" if judge(text)[0] == "ask" else None, EVERY),
]
# Why and Suggest for each reason. A Why is one short sentence and quotes at most a short piece of the value.
REASONS = {
    "blank": ("It has no value.", "Ask the person for the {slot} and write it here, or move it to Open as a question."),
    "no question": ("It sits in Open but does not end in a question mark, so it may be a decision.",
                    "Make it a question that ends in a question mark, or move it to Decided if it is settled."),
    "none": ('It says "none", so this slot may not be filled in yet.',
             "Confirm there is nothing for it, or write the real answer."),
    "placeholder": ("It has {word} in it, so part of it may not be filled in yet.",
                    "Write the missing part in the person's words, or confirm it as is if the word is meant."),
    "unknown": ('It says "unknown", so this may not be decided yet.',
                "Move it to Open as a question, or confirm it as is."),
    "question": ("It has a question mark, so it may be a question and not a decision.",
                 "Move it to Open if it is still a question, or confirm it as is if the answer quotes a question."),
    "hedge": ('It says "{word}", so the person may not have decided.',
              "Ask for a firm answer and write that, move it to Open as a question, or confirm it as is."),
    "trap": ('The word "{word}" can mean many things, so nobody can check it.',
             "Name something a person can see or count, or confirm it as is."),
    "insert": ("It has {word} in it, which may be template text left to fill in.",
               "Fill in the real text, or confirm it as is if the words in brackets are meant."),
    "hole": ("It has text in angle or curly brackets, which may be a template hole.",
             "Fill in the real text, or confirm it as is if the brackets are meant."),
    "vague": ("It is very short or vague, so it may not be a real answer.",
              "Write the full answer in the person's words, or confirm it as is."),
    "cases": ("Evals needs one case that should pass and one that should fail.",
              "Add a pass case and a fail case, for example `pass: …; fail: …`."),
}
# Wording one slot gives a reason. A Parked `out of scope:` line with a question mark may be a limit or a question.
SLOT_REASONS = {
    ("Parking lot", "question"): (
        "It is out of scope and has a question mark, so it may be a question and not a limit.",
        "Confirm it to keep it as a question for later, or drop the question mark if it is a firm limit."),
}
QUOTE_FALLBACK = {"placeholder": "a placeholder word", "insert": "a note in square brackets"}
# The drill-down: questions that narrow an answer toward an exact spec for that slot.
ASKS = {
    "Goal": ("What do you want to have at the end?", "Who is it for?"),
    "Done": ("What will you see when it is done?",),
    "Output": ("Who will see it, and where?", "What exactly should it show?", "How will you know it looks right?"),
    "Constraints": ("What must it never do?", "Is this a firm limit, or a wish?"),
    "Verification": ("What will you do to check it?", "What will you see if it works?"),
    "Tools": ("Which tool or app should it use?", "What must be ready before it starts?"),
    "Agents and roles": ("Who does the work?", "Who checks it?"),
    "Evals": ("What is one case that should pass?", "What is one that should fail?"),
    "Unknowns": ("What exactly do you want to find out?", "Who can answer it?"),
    "Parking lot": ("Is this for later, or out of scope?",),
}

Item = namedtuple("Item", "slot value why ask suggest clears")
# The one shared check's answer for one value. error is the format error ("blank" or "placeholder"), or None, and piece
# is the part of the value it is about. item is what to check with the person, or None. The script decides error.
# Only the person clears an item.
Verdict = namedtuple("Verdict", "error piece item")


def case_pieces(text):
    """(pieces, kinds, rest) of one Evals value. pieces are what check_brief reads: the text before the first colon
    label, and each case body of eval_cases. kinds holds pass and fail for those cases. rest is the text from each
    phrase to the next colon label or the end, which no case body holds, read with its phrase so it is never blank. A
    value with no case is one piece."""
    plain, marks = case_marks(text)
    cases, lead = eval_cases(text), eval_lead(text)
    pieces = [lead] * bool(core(lead)) + [body for _, body in cases]
    rest = [plain[start:after[0] if after else len(plain)]
            for (start, _, _, colon), after in zip(marks, marks[1:] + [None]) if not colon and (not after or after[3])]
    return pieces or [text], {kind for kind, _ in cases}, rest


def read_piece(text, role):
    """(error, reason, word) for one piece of text. See TRIGGERS."""
    if blank(text):
        return "blank", "blank", None
    if untouched(text):
        return "placeholder", None, None
    for reason, test, roles in TRIGGERS:
        word = test(text) if role in roles else None
        if word:
            return None, reason, word
    return None, None, None


def judge_value(slot, text, role=ANSWER):
    """The one check every value goes through: Verdict(error, item) for `text` in brief slot `slot`.

    The same text gets the same verdict in every slot. The slot only picks the wording and the Ask questions. An answer
    is read as its pieces, the way check_brief reads an Evals answer, so a short case is listed in any slot. Outside
    Evals the brief reads it whole too, so the whole text is read as well. The text after a phrase that no case body
    holds is read in every slot, so a sentence after the last case is judged.
    When an Evals answer has no pass case or no fail case, that is the item, and a yes cannot clear it.
    """
    pieces, kinds, rest = case_pieces(text) if role == ANSWER else ([text], set(), [])
    pieces += [text] * (slot != "Evals" and pieces != [text]) + rest
    reads = [read_piece(piece, role) for piece in pieces]
    error, piece = next(((error, piece) for (error, _, _), piece in zip(reads, pieces) if error), (None, None))
    reason, word = next(((reason, word) for _, reason, word in reads if reason), (None, None))
    if slot == "Evals" and role == ANSWER and not blank(text) and not {"pass", "fail"} <= kinds:
        reason, word = "cases", None
    if not reason:
        return Verdict(error, piece, None)
    why, suggest = SLOT_REASONS.get((slot, reason)) or REASONS[reason]
    word = quoted(word, QUOTE_FALLBACK[reason]) if reason in QUOTE_FALLBACK else word
    return Verdict(error, piece, Item(slot, text, why.format(word=word), " ".join(ASKS[slot]),
                               suggest.format(slot=slot.lower()), reason != "cases"))


Entry = namedtuple("Entry", "section row slot value text role label kind")
EXTRAS = ("tools", "agents", "evals", "decide", "write first")


def entries(found):
    """Every value in the file, once: Entry(section, row, brief slot, value as listed, text to judge, role, label, kind).

    This only finds the values. judge_value() judges them. label is what a replacement keeps in front of the new
    answer. kind is slot, extra (a tools:, agents:, evals:, decide: or write first: line) or line.
    """
    out = []
    for row in found["Decided"]:
        slot, value, label = landing(row)
        kind = "slot" if label in SLOTS else "extra" if label in EXTRAS else "line"
        # An `out of scope:` value is judged without its tag, as the brief check reads it, and keeps the tag.
        text = value[len(LIMIT):] if label == "out of scope" else value
        out.append(Entry("Decided", row, slot, value, text, ANSWER, f"{label}: " if label else "", kind))
    for row in found["Open"]:
        slot, value = open_key(row)
        name = slot_of(row) or (extra_of(row) or (None,))[0]
        out.append(Entry("Open", row, slot, value, open_body(row), QUESTION, f"{name}: " if name else "",
                         "slot" if slot_of(row) else "line"))
    for row in found["Parked"]:
        if is_none(row):
            continue
        if OUT_OF_SCOPE.match(row.strip()):
            slot = "Parking lot" if has_question(row) else "Constraints"
            out.append(Entry("Parked", row, slot, scoped(row), scoped(row)[len(LIMIT):], ANSWER, LIMIT, "line"))
        else:
            out.append(Entry("Parked", row, "Parking lot", parked_value(row), landing(row)[1], NOTE, "", "line"))
    return out


def review(text):
    """Every CHECK WITH ME Item, before confirmations, in file order, one per slot and value."""
    unique = {}
    for entry in entries(sections_of(text)):
        item = judge_value(entry.slot, entry.text, entry.role).item
        if not item:
            continue
        item = item._replace(value=entry.value)
        key = (item.slot, item.value)
        # An item a yes cannot clear wins, so its advice is not hidden behind one a yes clears.
        if key not in unique or unique[key].clears and not item.clears:
            unique[key] = item
    return list(unique.values())


def bar(text):
    """Text as a confirmed.md line writes it, so a bar or a backslash in it is read back as itself. See unbar()."""
    return text.replace("\\", "\\\\").replace("|", "\\|")


def unbar(text):
    """The pieces of confirmed.md text between unescaped bars, each \\| and \\\\ read back."""
    pieces, piece = [], ""
    for token in BAR_TOKEN.findall(text):
        if token == "|":
            pieces, piece = pieces + [piece], ""
        else:
            piece += token[1] if len(token) == 2 and token[0] == "\\" else token
    return [part.strip() for part in pieces + [piece]]


def read_confirmed(text):
    """([(slot, value, answer)] in file order, [fails]) from confirmed.md text. answer is `yes` or the new answer."""
    answers, fails = [], []
    for raw in (text or "").lstrip("﻿").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = CONFIRMED_LINE.match(line)
        pieces = unbar(match["rest"]) if match else []
        if len(pieces) != 2 or not all(pieces):
            fails.append(f"confirmed.md line {line!r} is not `- <Slot>: <value> | yes` or `- <Slot>: <value> | <new"
                         " answer>`. Write a bar inside the value or the answer as `\\|`")
        elif pieces[1].lower() == "no":
            fails.append(f"confirmed.md line {line!r} says no. Write the new answer after the bar in place of no")
        else:
            value, answer = pieces
            answers.append((match["slot"].strip(), value, "yes" if answer.lower() == "yes" else answer))
    return answers, fails


def rows_of(lines, entry):
    """The index of each line in `lines` that holds `entry`, as the file writes it."""
    section, out = None, []
    for i, line in enumerate(lines):
        head = HEAD.match(line.strip())
        if head:
            section = canon(head.group(1))
            continue
        bullet = BULLET.match(line)
        if section == entry.section and bullet and bullet.group(1).strip() == entry.row:
            out.append(i)
    return out


def replaced(text, entry, new):
    """The decisions text with the line of `entry` holding `new` in place of its value. The label stays, once: a new
    answer that starts with it or another name for it (`tool:` for `tools:`), in any case and spacing, bold or italic
    as the parser reads a label (`**Tool:**`), is written with one space after its colon."""
    name = entry.label.rstrip(": ")
    if name:
        names = {name} | {alias for alias, canonical in EXTRA_NAME.items() if canonical == name}
        spelled = "|".join(r"\s+".join(map(re.escape, n.split())) for n in sorted(names, key=len, reverse=True))
        new = re.sub(rf"^[*_]*(?:{spelled})[*_]*\s*[:：][*_]*\s*", "", new, flags=re.I)
    lines = text.split("\n")
    for i in rows_of(lines, entry):
        lines[i] = f"{lines[i][0]} {entry.label}{new}"
    return "\n".join(lines)


def has_error(entry, text):
    """True when the entry's line in `text` has a format error, from the shared check or the writing check. The writing
    check reads the whole line as the file holds it, the same view the check of the whole file has."""
    lines = text.split("\n")
    return bool(judge_value(entry.slot, entry.text, entry.role).error
                or prose_fails("\n".join(lines[i] for i in rows_of(lines, entry))))


def listed(entry, text):
    """True when the shared check lists the entry for the person and its line has no format error."""
    return judge_value(entry.slot, entry.text, entry.role).item is not None and not has_error(entry, text)


def merged(first, second):
    """Two runs of the format checks as one, by check name. A fail from either run stays."""
    out = {}
    for name, fails in first + second:
        out[name] = out.get(name, []) + [fail for fail in fails if fail not in out.get(name, [])]
    return list(out.items())


def settle(text, answers):
    """(steps, yes, swapped, stale) for the answers. The latest line for a slot and value wins.

    steps is the decisions text after each replacement, in confirmed.md order, so the last one is what the mapper maps.
    yes is the (slot, value) of each latest yes whose value is in the text when that yes applies. stale is each other
    latest yes: it clears nothing, not even a value a later line writes. swapped is the (slot, value) of each
    replacement made. The new answer sits where the old value was, so a later line can answer it, and the order of the
    lines in decisions.md does not matter. Each line applies once, to every line with that slot and value it finds
    then. A replacement only answers an item: it never replaces a value with a format error.
    """
    latest = {}
    for slot, value, answer in answers:
        latest.pop((slot, value), None)
        latest[(slot, value)] = answer
    steps, yes, swapped, stale = [text], [], [], []
    for key, answer in latest.items():
        here = [e for e in entries(sections_of(steps[-1])) if (e.slot, e.value) == key]
        if answer == "yes":
            (yes if here else stale).append(key)
            continue
        found = [e for e in here if listed(e, steps[-1])]
        if not found:
            continue
        swapped.append(key)
        new = steps[-1]
        for entry in found:
            new = replaced(new, entry, answer)
        steps.append(new)
    return steps, yes, swapped, stale


Result = namedtuple("Result", "code results pending notes used text broken")


def verdict(text, confirmed_text=""):
    """The one result both scripts print. code is 0 pass, 1 format invalid, 2 check with me.

    results are the format checks, which only the script decides. pending are the items no person has answered yet.
    used are the (slot, value) of each yes that cleared an item. broken are the (slot, value) of each listed or answered
    value whose own line has a format error in decisions.md or after any replacement, which no answer clears. text is
    the decisions text with each replacement in place, which is what the mapper maps.
    """
    answers, confirm_fails = read_confirmed(confirmed_text)
    # The format checks read decisions.md as written, so no answer clears a format error. Each new answer is read again
    # in its place, at every step, so it can add an error or an item, and a later answer never removes one.
    steps, yes, swapped, stale = settle(text, answers)
    results = check(text)
    for step in steps[1:]:
        results = merged(results, check(step))
    text = steps[-1]
    results.append((CONFIRMED_CHECK, confirm_fails))
    failed = any(fails for _, fails in results)
    found = review(text)
    keys = {(item.slot, item.value) for item in found}
    pending = [item for item in found if not (item.clears and (item.slot, item.value) in yes)]
    used = [key for key in yes if key in keys]
    # A yes that comes before the line that writes its value. A yes for a value no line ever writes matches nothing.
    early = set(stale) & {(e.slot, e.value) for step in steps for e in entries(sections_of(step))}
    named = {(slot, value) for slot, value, _ in answers} | {(item.slot, item.value) for item in pending}
    broken = {(e.slot, e.value) for step in steps for e in entries(sections_of(step))
              if (e.slot, e.value) in named and has_error(e, step)}
    notes = [f"NOTE: confirmed.md line '- {slot}: {bar(value)} | {bar(answer)}' "
             + ("names a value with a format error. Fix it in decisions.md, because no answer clears it"
                if (slot, value) in broken else "comes before the line that writes that value, so it clears nothing."
                " Move it below that line" if (slot, value) in early and answer == "yes"
                else "matches nothing in decisions.md now; remove it")
             for slot, value, answer in dict.fromkeys(answers)
             if (slot, value) in broken or (slot, value) not in keys | set(swapped)
             or (slot, value) in early and answer == "yes"]
    if not failed and not pending:
        # Once every item is answered, the brief must pass check_brief whole. A value it still asks about here is a
        # gap in the shared check, so it fails, and a yes cannot hide it.
        asked = [line for _, _, line in brief_asks(mapped(text, used))]
        results.append((BRIEF_CHECK + " with every answer", asked))
        failed = bool(asked)
    code = 1 if failed else 2 if pending else 0
    return Result(code, results, pending, notes, used, text, broken)


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
            lines += [f'- {item.slot}: "{item.value}"', f"  Why: {item.why}", f"  Ask: {item.ask}",
                      f"  Suggest: {item.suggest}"]
            if (item.slot, item.value) not in result.broken:
                lines.append(f"  Line: - {item.slot}: {bar(item.value)} | {'yes' if item.clears else '<new answer>'}")
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


def utf8_output():
    """Prints UTF-8 whatever the locale says, so a value in any script prints. A character that cannot print is
    replaced, never a crash."""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")


def unreadable(path, why):
    """Prints the one usage line for a path that cannot be read, and returns exit 3."""
    print(f"usage: cannot read {path}: {why}", file=sys.stderr)
    return 3


def inputs(path, confirmed=None):
    """(decisions text, confirmed.md text, None), or (None, None, exit 3) after one usage line on stderr.

    Without --confirmed, confirmed.md next to decisions.md is read when that path exists. A directory there is the
    same usage error as one named with --confirmed.
    """
    text, why = read(path)
    if why:
        return None, None, unreadable(path, why)
    beside = os.path.join(os.path.dirname(path), "confirmed.md")
    if confirmed is None and not os.path.exists(beside):
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
    utf8_output()
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__.strip())
        sys.exit(0)
    args = arguments(sys.argv[1:], "usage: python3 check/check_decisions.py <decisions.md> [--confirmed <confirmed.md>]")
    sys.exit(3 if args is None else main(*args))
