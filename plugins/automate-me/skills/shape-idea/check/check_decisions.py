"""Checks the shape of a decisions.md written by the shape-idea skill.

Usage: python3 check/check_decisions.py <decisions.md>

Sections are `## Decided`, `## Open`, `## Parked`, and `## Handoff`, in that order, each once.
An optional `## Confirmed` section may follow Handoff (see Asks below).
An item is one top-level bullet (`- ` or `* `). A later physical line under a section is an item
that ran past one line. A section whose only item is `none` has no items. Handoff holds:

    - next: /automate-me:outcome
    - stop: done | turn-cap | open-cap
    - turns: <n>
    - writing: pass

The five slots are goal, done, output, verify, and constraints. A slot counts when a Decided
or Open item starts with `<slot>:` and the value after the colon is not empty. An Open example
is `output: what comes back, a list or a page?`. A slot in Parked does not count. A line such
as `goalpost:` is not the goal slot.

The open cap counts Open items that are not those five slots. `stop: open-cap` is valid only
when that count is more than 5 and `turns` is from 2 through 10. It is never valid on turn 1.
`stop: turn-cap` is valid only when `turns` is 10. `stop: done` is valid only when all five
slots are Decided lines and none of them is also Open.

`turns` is parsed as ASCII digits only (`^[0-9]+$`), from 1 through 10. `0`, negatives, and
a unicode digit such as `²` fail, and they do not crash the check.

The checker runs the shared writing check on the file. A `writing: pass` line does not
override a writing failure.

Values are judged by outcome's check_brief, on the brief itself. Once the shape checks pass, the file is mapped
with outcome's map_decisions.map_text(), and check_brief's check() and asks() run on that brief. Each line the
mapper prefixes with `stated:` is judged again without it, so the prefix hides nothing. The mapper uses the same
result, so it prints a brief only when check_brief passes it.

Fails (exit 1) when:
- the file has no `# Decisions` title;
- a section is missing or repeated, or the sections are out of order;
- a code fence sits under Decided, Open or Parked, because its text would not reach the brief;
- an Open item does not end with `?`, or `?` and closing quotes or brackets. Only the end counts. The question after
  any slot, line or `unknown:` label is only a placeholder such as `?` or `TBD?`, or holds a template hole;
- a Decided value ends in `?`;
- an answer is an unknown. An answer is a Decided value, an Evals case body, or a Parked `out of scope:` line.
  Once check_brief's core() strips markup and `stated:` is gone, it is `unknown` alone, `unknown` and punctuation,
  or `unknown` and at most three words (`unknown for now`). It belongs in Open as a question;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line is empty or
  repeated. Bold and a singular label (`**tools:**`, `tool:`, `eval:`) name the same line;
- a slot is missing from both Decided and Open, is repeated, is in both, or has an empty value.
  A slot written as `**goal:**` or `1. goal:` gets its own message;
- stop is missing, repeated, or not one of done, turn-cap, open-cap;
- stop does not match the file (done, open-cap, or turn-cap rules above);
- turns is missing, repeated, or not a whole number from 1 through 10;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line, no single `writing: pass` line, or not one `map:` line;
- a Confirmed line is not `<Slot>: <value>` with a brief slot label;
- the shared writing check fails;
- check_brief fails the mapped brief.

Asks (exit 2, when nothing fails):
- for each value check_brief asks about on the mapped brief, such as `ok` in a slot, a hole inside a longer line,
  an Evals line with no pass or fail case, or a Parked `out of scope: AI`. It prints check_brief's ASK line,
  `ASK: <slot>: Is '<value>' a real answer for <slot>?`;
- for each answer that starts with `unknown` and is longer than the fails above, such as `unknown file types go
  to Other`. It prints `ASK: <slot>: Is '<value>' decided, or still unknown?`.
This is the break point: stop, ask the person that yes/no question, and record the answer. A yes goes under
`## Confirmed` at the end of the file as `- <Slot>: <value>`, and the mapper copies it into the brief. A no
replaces the value, or moves the slot to Open as a question. A confirmation never lifts a fail.

Prints a PASS or FAIL line per check, then the ASK lines, then `PASS|FAIL|ASK decisions: <path>`.
Exit 0 pass, 1 fail, 2 ask, 3 usage: bad arguments, or a path that is missing, a directory, or not
UTF-8 text, with one line on stderr. A UTF-8 BOM is ignored.
"""
import contextlib
import io
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared")))
from check_writing import check_writing  # noqa: E402

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "outcome", "check")))
from check_brief import ask_lines, asks as brief_asks, check as check_brief, core, eval_cases, judge  # noqa: E402
from check_brief import parse as parse_brief  # noqa: E402

SECTIONS = ["Decided", "Open", "Parked", "Handoff"]
HEAD = re.compile(r"^##\s+(Decided|Open|Parked|Handoff|Confirmed)\s*$", re.I)
BULLET = re.compile(r"^[-*]\s+(.*)$")
STOPS = {"done", "turn-cap", "open-cap"}
NEXT = "next: /automate-me:outcome"
TITLE = re.compile(r"^# Decisions\b", re.M)
MAX_TURNS = 10
OPEN_CAP = 5
SLOTS = ["goal", "done", "output", "verify", "constraints"]
# A slot label may have spaces before the colon, and the colon may be full-width.
# `Output : value` and `output： value` are the output slot. `goalpost:` is not goal.
SLOT_HEAD = re.compile(r"^(goal|done|output|verify|constraints)\s*[:\uff1a]\s*(.*)$", re.I)
OUT_OF_SCOPE = re.compile(r"^[*_]*out of scope[*_]*\s*:[*_]*\s*", re.I)
ASCII_DIGITS = re.compile(r"^[0-9]+$")
# A fence is ``` or ~~~, three or more, with optional info. A closer matches the
# innermost fence's character and length and has no info. A different length or
# the other character opens a nested fence. Text inside any of them is hidden.
FENCE_LINE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HANDOFF_FIELD = re.compile(r"^(next|stop|turns|writing|map)\s*[:\uff1a]\s*(.*)$", re.I)
# A tools:, agents:, evals:, decide: or write first: label. Bold, italics and a singular label still name that line.
EXTRA_HEAD = re.compile(r"^[*_]*(tools?|agents and roles|agents?|evals?|decide|write first)[*_]*\s*[:\uff1a][*_]*\s*(.*)$",
                        re.I)
EXTRA_NAME = {"tool": "tools", "agent": "agents", "agents and roles": "agents", "eval": "evals"}
# An Open item is a question when it ends with `?`, or `?` and closing quotes or brackets. Nothing else counts.
QUESTION_END = re.compile(r"\?[\"'\u201d\u2019)\]]*$")
LOOSE_SLOT = re.compile(r"^(?:\d+[.)]\s*)?[*_]+\s*(goal|done|output|verify|constraints)\s*[*_]*\s*[:\uff1a]"
                        r"|^\d+[.)]\s*(goal|done|output|verify|constraints)\s*[:\uff1a]", re.I)
BRIEF_SLOT = {"goal": "Goal", "done": "Done", "output": "Output", "verify": "Verification",
              "constraints": "Constraints", "tools": "Tools", "agents": "Agents and roles", "evals": "Evals",
              "decide": "Goal", "write first": "Tools"}
STATED = re.compile(r"^\s*[*_`]*\s*stated\s*[*_`]*\s*:\s*[*_`]*\s*", re.I)
UNKNOWN_LEAD = re.compile(r"^unknown(?![^\W_])(.*)$")
SHORT_TAIL = 3
VALUE_CHECKS = {"no placeholder", "no template hole", "no bare trap adjective"}
MAPPED_STATED = re.compile(r"^(\s+- )stated: ", re.M)


def canon(name):
    return next(s for s in SECTIONS + ["Confirmed"] if s.lower() == name.lower())


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
    Headings and slots inside a fence are hidden, so they do not count as structure.
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
    """The value with every leading `stated:` label gone, bold or not. The rules judge what is left."""
    text = (value or "").strip()
    while STATED.match(text):
        text = STATED.sub("", text, count=1).strip()
    return text


def unknown_shape(value):
    """'question' when an answer is an unknown that belongs in Open, 'ask' when it only starts with the word, else None.

    The value is read as check_brief's core() reads it, so markup and a `stated:` label hide nothing. `unknown` alone,
    `unknown` and punctuation (`unknown:`, `unknown,`, `unknown (`), or `unknown` and at most three words is a question.
    A longer value may be prose such as `unknown file types go to Other`, so the person says whether it is decided.
    """
    match = UNKNOWN_LEAD.match(core(unstated(value)))
    if not match:
        return None
    tail = match.group(1)
    if not tail.strip() or not tail[0].isspace() or not tail.split()[0][0].isalnum() or len(tail.split()) <= SHORT_TAIL:
        return "question"
    return "ask"


def undecided(source, value):
    """Why an answer is not a decision yet, or None."""
    if source == "Decided" and value.endswith("?"):
        return "is a question, not a decision; move it to Open"
    if unknown_shape(value) == "question":
        return "is unknown; move it to Open as a question"
    return None


def open_body(item):
    """An Open item's question without its slot or line label and without leading `unknown:` or `stated:`."""
    extra = extra_of(item)
    text = slot_value(item) if slot_of(item) else extra[1] if extra else item
    return re.sub(r"^(?:\s*(?:unknown|stated)\s*:)+", "", text, flags=re.I).strip()


def scoped(item):
    """An `out of scope:` line, bold or not, as the brief writes it in Constraints."""
    return "out of scope: " + OUT_OF_SCOPE.sub("", item.strip(), count=1)


def extra_of(item):
    """(name, value) when the line is tools:, agents: (or agents and roles:), evals:, decide:, or write first:."""
    match = EXTRA_HEAD.match(item.strip())
    if not match:
        return None
    name = match.group(1).lower()
    return EXTRA_NAME.get(name, name), match.group(2).strip()


def is_question(item):
    return bool(QUESTION_END.search(item.strip()))


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


def check(text):
    visible, hidden, unclosed, fenced = split_fences(text.lstrip("\ufeff"))
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
    if counts.get("Confirmed", 0) > 1:
        present.append(f"section Confirmed appears {counts['Confirmed']} times")
    for name in SECTIONS:
        n = counts.get(name, 0)
        if n == 0:
            present.append(f"missing section: {name}")
        elif n != 1:
            present.append(f"section {name} appears {n} times")
    add("sections present once", present)

    order = []
    if all(counts.get(name) == 1 for name in SECTIONS) and positions not in (SECTIONS, SECTIONS + ["Confirmed"]):
        order.append("sections are " + ", ".join(positions) + "; use Decided, Open, Parked, Handoff, then Confirmed if any")
    add("sections in order", order)

    decided = real_items(sections.get("Decided", []))
    opens = real_items(sections.get("Open", []))
    q_fails = []
    for item in opens:
        outcome, why = judge(open_body(item))
        if not is_question(item):
            q_fails.append(f"open item needs a question mark at the end: {item!r}")
        elif why == "hole":
            q_fails.append(f"open item holds a template hole; fill it: {item!r}")
        elif outcome == "fail":
            q_fails.append(f"open item is a placeholder, not a question: {item!r}")
    add("every open item ends with a question", q_fails)
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

    dup_fails = []
    both_fails = []
    empty_fails = []
    for slot in SLOTS:
        in_decided = [item for item in decided if slot_of(item) == slot]
        in_open = [item for item in opens if slot_of(item) == slot]
        if len(in_decided) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_decided)} Decided lines")
        if len(in_open) > 1:
            dup_fails.append(f"slot {slot} is on {len(in_open)} Open lines")
        if in_decided and in_open:
            both_fails.append(f"slot {slot} is both Decided and Open")
        for item in in_decided + in_open:
            value = slot_value(item)
            if value is None or value.strip().strip("?").strip() == "":
                empty_fails.append(f"slot {slot} has an empty value: {item!r}")
    add("no duplicate slot", dup_fails)
    add("a slot is not in Decided and Open", both_fails)
    add("slot values are not empty", empty_fails)

    extra_fails = []
    seen_extra = set()
    for name, value in filter(None, map(extra_of, decided)):
        if name in seen_extra:
            extra_fails.append(f"{name}: is on more than one Decided line")
        seen_extra.add(name)
        if not value:
            extra_fails.append(f"{name}: needs a value")
    add("tools, agents, evals, and decide lines are usable", extra_fails)

    parked = real_items(sections.get("Parked", []))
    add("Decided values are decisions",
        [f"{slot}: {value!r} {why}" for source, slot, value in answers(decided, parked)
         for why in [undecided(source, value)] if why])

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
    first_fails = []
    if first and stop and stop != first:
        first_fails.append(f"stop is {stop} but the first match is {first}")
    add("stop is the first match", first_fails)
    overflow = []
    if turn_number == 1 and len(non_slot) > OPEN_CAP:
        overflow.append(
            f"turn 1 has {len(non_slot)} open items that are not slots; park the ones past {OPEN_CAP}")
    add("turn 1 parks overflow", overflow)

    add("no item longer than one line",
        [f"{name}: extra line {text!r}. Each item stays on one line" for name, text in extras])

    nexts = [value.strip() for value in fields["next"]]
    next_fails = []
    if handoff_ready and nexts != ["/automate-me:outcome"]:
        next_fails.append(f"Handoff next is {nexts!r}; write one `{NEXT}` line")
    add("handoff names outcome", next_fails)

    confirmed_fails = [f"Confirmed line {item!r} is not `<Slot>: <value>` with a brief slot such as Output"
                       for item in sections.get("Confirmed", []) if not parse_brief("## Confirmed\n- " + item)[3]]
    add("confirmed lines name a brief slot", confirmed_fails)

    maps = fields["map"]
    map_fails = []
    if handoff_ready and len(maps) != 1:
        map_fails.append("Handoff needs one map: line, as the template shows")
    add("handoff has a map line", map_fails)

    writing = [value.lower() for value in fields["writing"]]
    writing_fails = []
    if handoff_ready and writing != ["pass"]:
        writing_fails.append("Handoff has no single `writing: pass` line. Run the shared writing check first")
    add("handoff says writing pass", writing_fails)
    prose = visible if not hidden else visible + "\n" + hidden
    add("prose passes the writing check", prose_fails(prose))
    if not any(fails for _, fails in results):
        add("the mapped brief passes outcome's brief check", brief_findings(text)[0])
    return results


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
    """(source, brief slot, value) for every answer the brief will hold: each Decided value, each Evals case body,
    and each Parked `out of scope:` line, which the mapper puts in Constraints."""
    out = []
    for slot, value, label in map(landing, decided):
        out += [("Decided", slot, value)] if value else []
        out += [("Decided", slot, body.strip().rstrip(";,").strip()) for _, body in eval_cases(value)] if label == "evals" else []
    return out + [("Parked", "Constraints", scoped(row)) for row in parked if OUT_OF_SCOPE.match(row.strip())]


def brief_findings(text):
    """(fails, asks) from outcome's check_brief on the brief the mapper writes for `text`. asks are (slot, value, line).

    The mapper puts `stated:` in front of a line whose tag belongs in another slot. check_brief judges the brief as
    written, and judges each value again without that prefix, so the prefix hides no placeholder, hole, trap or ask.
    """
    import map_decisions  # map_decisions imports this module, so it is loaded on first use.

    brief = map_decisions.map_text(text)
    plain = MAPPED_STATED.sub(r"\1", brief)
    fails = [fail for _, items in check_brief(brief) for fail in items]
    fails += [fail for name, items in check_brief(plain) if name in VALUE_CHECKS for fail in items if fail not in fails]
    asked = []
    for found in (brief, plain):
        asked += [(slot, value, line) for (slot, value), line in zip(brief_asks(found), ask_lines(found))
                  if (slot, value) not in [(s, v) for s, v, _ in asked]]
    return fails, asked


def found_asks(text):
    """(slot, value, ASK line) for each value a person must confirm: what check_brief asks on the mapped brief, and
    each answer that starts with `unknown` but may be prose. A `## Confirmed` line lifts either."""
    visible = split_fences(text.lstrip("\ufeff"))[0]
    sections = parse(visible)[0]
    confirmed = parse_brief("## Confirmed\n" + "\n".join(f"- {item}" for item in sections.get("Confirmed", [])))[3]
    asked = brief_findings(text)[1]
    for _, slot, value in answers(real_items(sections.get("Decided", [])), real_items(sections.get("Parked", []))):
        if unknown_shape(value) == "ask" and (slot, core(value)) not in confirmed:
            asked.append((slot, value, f"ASK: {slot}: Is '{value}' decided, or still unknown?"))
    return asked


def asks(text):
    """(slot, value) for each value a person must confirm."""
    return [(slot, value) for slot, value, _ in found_asks(text)]


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


def report(text, path):
    """(exit code, printed lines). 0 pass, 1 fail, 2 ask."""
    lines, failed = [], False
    for name, fails in check(text):
        lines.append(f"{'FAIL' if fails else 'PASS'} {name}")
        lines += [f"  {fail}" for fail in fails]
        failed = failed or bool(fails)
    asked = [] if failed else found_asks(text)
    lines += [line for _, _, line in asked]
    verdict = "FAIL" if failed else "ASK" if asked else "PASS"
    lines.append(f"{verdict} decisions: {path}")
    return {"FAIL": 1, "ASK": 2, "PASS": 0}[verdict], lines


def main(path):
    text, why = read(path)
    if why:
        return unreadable(path, why)
    code, lines = report(text, path)
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) == 2 else 3)
    sys.exit(main(sys.argv[1]))
