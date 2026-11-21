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

Values are judged by outcome's check_brief: classify() says pass, fail or ask. Its fixed list is
deliberately narrow. A phrase off that list passes here and is left to the ask or the read-back.
Every Decided line is judged by the same rules, whatever its label. A leading `stated:`, bold or
not, is dropped first, so it hides nothing.

Fails (exit 1) when:
- the file has no `# Decisions` title;
- a section is missing or repeated, or the sections are out of order;
- a code fence sits under Decided, Open or Parked, because its text would not reach the brief;
- an Open item does not end with one `?`, or is only a placeholder such as `?`, `TBD?` or `unknown: ?`.
  A `?` inside inline code, a URL, quotes (single, double or curly) or parens does not count;
- any item holds a template hole such as `<channel>`, outside inline code;
- a Decided line that is not a slot, or a Parked line, is only a placeholder such as `TBD` or `later, perhaps`;
- a slot value classifies as fail (a placeholder or a template hole), or any Decided value ends in `?`;
- a Decided value, or a Parked line, is not ready for the brief. It is an unknown: once check_brief's
  core() strips markup (bold, italics, quotes, parens, one tag label), it is `unknown` alone,
  `unknown: ...`, or `unknown` and a tail classify() does not pass, such as `yet`. Prose such as
  `unknown file types go to Other` is not. Or it is only a trap word. A slot value also fails when it
  starts with a brief tag outside its home (`investigate:` Done, `out of scope:` Constraints, `how:`
  Agents and roles), or when a Goal value starts with `default` while Goal holds an unknown, that is
  when no `decide:` line or no goal is Decided;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line
  is empty, fails, is a question, is not ready as above, or is repeated. An `evals:` line fails as
  check_brief would fail it, so every case body must pass, and it needs a pass case and a fail case
  (check_brief's eval_cases: `pass: <case>; fail: <case>` or `<case> should pass, <case> should fail`);
- a slot is missing from both Decided and Open, is repeated, is in both, or has an empty value.
  A slot written as `**goal:**` or `1. goal:` gets its own message;
- stop is missing, repeated, or not one of done, turn-cap, open-cap;
- stop does not match the file (done, open-cap, or turn-cap rules above);
- turns is missing, repeated, or not a whole number from 1 through 10;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line, or no single `writing: pass` line;
- a Confirmed line is not `<Slot>: <value>` with a brief slot label;
- the shared writing check fails.

Asks (exit 2, when nothing fails) for each Decided value that check_brief would ask about, placed
in the brief slot the mapper puts it in (a line that is not a slot lands in Done). It prints
`ASK: <slot>: Is '<value>' a real answer for <slot>?`. This is the break point: stop, ask the
person that yes/no question, and record the answer. A yes goes under `## Confirmed` at the end of
the file as `- <Slot>: <value>`, and the mapper copies it into the brief. A no replaces the value,
or moves the slot to Open as a question. A confirmation never lifts a fail.

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
from check_brief import asks as brief_asks, check as check_brief, classify, core, eval_cases, judge  # noqa: E402
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
EXTRA_HEAD = re.compile(r"^(tools|agents and roles|agents|evals|decide|write first)\s*[:\uff1a]\s*(.*)$", re.I)
# Spans whose `?` is not the question's end: code, a URL, and text in quotes or parens.
URL_OR_CODE = re.compile(r"`[^`]*`|https?://\S+|\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d|(?<!\w)'[^'\n]*'(?!\w)"
                         r"|\u2018[^\u2019\n]*\u2019|\([^()\n]*\)")
LOOSE_SLOT = re.compile(r"^(?:\d+[.)]\s*)?[*_]+\s*(goal|done|output|verify|constraints)\s*[*_]*\s*[:\uff1a]"
                        r"|^\d+[.)]\s*(goal|done|output|verify|constraints)\s*[:\uff1a]", re.I)
BRIEF_SLOT = {"goal": "Goal", "done": "Done", "output": "Output", "verify": "Verification",
              "constraints": "Constraints", "tools": "Tools", "agents": "Agents and roles", "evals": "Evals",
              "decide": "Goal", "write first": "Tools"}
# A brief tag and the one brief slot where it may lead an item.
TAG_LEAD = re.compile(r"^(investigate|out of scope|how)\s*:", re.I)
TAG_HOME = {"investigate": "Done", "out of scope": "Constraints", "how": "Agents and roles"}
DEFAULT_LEAD = re.compile(r"^default\b", re.I)
STATED = re.compile(r"^\s*[*_`]*\s*stated\s*[*_`]*\s*:\s*[*_`]*\s*", re.I)
UNKNOWN_WORD = re.compile(r"^unknown\b\s*(:?)(.*)$")


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


def is_unknown(value):
    """`unknown` alone, `unknown: ...`, or `unknown` and a hedge such as `yet`, once markup is gone.

    Markup is check_brief's core(): italics, bold, quotes, parens and one tag label. Prose such as
    `unknown file types go to Other` is not an unknown.
    """
    match = UNKNOWN_WORD.match(core(unstated(value)))
    return bool(match) and (bool(match.group(1)) or classify(match.group(2)) != "pass")


def unready(value, decided=True):
    """Why a Decided or Parked value is not ready for the brief, or None. A `stated:` prefix hides nothing.

    A placeholder or a template hole fails. A Decided value that ends in `?` is a question. An unknown
    stays a question, so it belongs in Open. A bare trap word names no signal.
    """
    plain = unstated(value)
    outcome, why = judge(plain)
    if outcome == "fail":
        return "holds a template hole; fill it" if why == "hole" else "is a placeholder"
    if decided and plain.endswith("?"):
        return "is a question, not a decision; move it to Open"
    if is_unknown(plain) and not plain.endswith("?"):
        return "is unknown; move it to Open as a question"
    if is_trap(plain):
        return "names no visible signal; say what you will see"
    return None


def question(item):
    """An Open item as the brief asks it, with any leading `unknown:` or `stated:` gone."""
    return re.sub(r"^(?:\s*(?:unknown|stated)\s*:)+", "", item, flags=re.I).strip()


def misplaced(value, slot):
    """Why a slot value starts with a brief tag that belongs in another slot, or None."""
    tag = TAG_LEAD.match(re.sub(r"\*\*|__|`", "", unstated(value)))
    if tag and TAG_HOME[tag.group(1).lower()] != slot:
        return f"starts with {tag.group(0)!r}, a brief tag that belongs in {TAG_HOME[tag.group(1).lower()]}; reword it"
    return None


def brief_item(text, slot):
    """A line that is not a slot, as the mapper writes it in brief slot `slot` (Done or Parking lot).

    When it starts with a brief tag outside its home, or with `default`, `stated:` goes in front.
    The words stay. Unknowns, trap words and placeholders never get here: the check fails them.
    """
    raw = text.strip()
    tag = TAG_LEAD.match(raw)
    if (tag and TAG_HOME[tag.group(1).lower()] != slot) or DEFAULT_LEAD.match(raw):
        return f"stated: {raw}"
    return raw


def scoped(item):
    """An `out of scope:` line, bold or not, as the brief writes it in Constraints."""
    return "out of scope: " + OUT_OF_SCOPE.sub("", item.strip(), count=1)


def is_trap(text):
    """True when check_brief's check() reads `text` in a slot as only trap words."""
    return bool(dict(check_brief(f"- Goal: {text}\n"))["no bare trap adjective"])


def has_hole(item):
    return judge(item)[1] == "hole"


def extra_of(item):
    """(name, value) when the line is tools:, agents: (or agents and roles:), evals:, decide:, or write first:."""
    match = EXTRA_HEAD.match(item.strip())
    if not match:
        return None
    name = match.group(1).lower()
    return "agents" if name == "agents and roles" else name, match.group(2).strip()


def is_question(item):
    """The item ends with ? and has no other ? outside inline code, a URL, or a quote."""
    text = item.strip()
    return text.endswith("?") and "?" not in URL_OR_CODE.sub("", text[:-1])


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
        if not is_question(item):
            q_fails.append(f"open item needs one question at the end: {item!r}")
        elif not slot_of(item) and classify(question(item)) == "fail":
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

    lands = [landing(item) for item in decided]
    labels = [label for _, _, label in lands]
    goal_unknown = "goal" not in labels or "decide" not in labels

    def goal_default(value, slot):
        if slot == "Goal" and goal_unknown and DEFAULT_LEAD.match(unstated(value)):
            return "starts with 'default', which the brief reads as a default beside an unknown in Goal; reword it"
        return None

    ph_fails = []
    for slot in SLOTS:
        for item in (row for row in decided if slot_of(row) == slot):
            value = slot_value(item) or ""
            why = value and (unready(value) or misplaced(value, BRIEF_SLOT[slot]) or goal_default(value, BRIEF_SLOT[slot]))
            if why:
                ph_fails.append(f"slot {slot} {why}: {value!r}")
        for item in (row for row in opens if slot_of(row) == slot):
            value = slot_value(item) or ""
            if value and classify(question(value)) == "fail":
                ph_fails.append(f"slot {slot} is a placeholder: {value!r}")
    add("slot values are not placeholders", ph_fails)

    extra_fails = []
    seen_extra = {}
    for item in decided:
        got = extra_of(item)
        if not got:
            continue
        name, value = got
        if name in seen_extra:
            extra_fails.append(f"{name}: is on more than one Decided line")
        seen_extra[name] = value
        if name == "write first" and core(value) == "none":
            continue
        if not value or classify(value) == "fail" or value.endswith("?"):
            extra_fails.append(f"{name}: needs a real value, not a placeholder or a question")
            continue
        if name == "evals":
            extra_fails += [f"evals: {fail}" for check_name, fails in check_brief(f"- Evals: {value}\n")
                            if check_name in ("no placeholder", "no template hole") for fail in fails]
        cases = eval_cases(value) if name == "evals" else []
        why = next(filter(None, (unready(part) or misplaced(part, BRIEF_SLOT[name]) or goal_default(part, BRIEF_SLOT[name])
                                 for part in [value] + [b for _, b in cases if classify(b) != "fail"])), None)
        if why:
            extra_fails.append(f"{name}: {why}: {value!r}")
            continue
        if name == "evals" and {kind for kind, _ in cases} != {"pass", "fail"}:
            extra_fails.append("evals: needs a pass case and a fail case, in the user's words."
                               " Write `pass: <case>; fail: <case>` or `<case> should pass, <case> should fail`")
    add("tools, agents, evals, and decide lines are usable", extra_fails)

    parked = real_items(sections.get("Parked", []))
    others = [("Decided", item) for item, (_, _, label) in zip(decided, lands) if label in (None, "out of scope")]
    others += [("Parked", item) for item in parked]
    add("no placeholder line",
        [f"{name}: {item!r} is a placeholder; say what it is or remove it" for name, item in others
         if judge(unstated(item)) == ("fail", "placeholder")])
    add("no template hole",
        [f"{name}: {item!r} holds a template hole; fill it"
         for name, item in others + [("Open", item) for item in opens if not slot_of(item) and not extra_of(item)]
         if has_hole(unstated(item))])
    add("other Decided and Parked lines are ready",
        [f"{name}: {item!r} {unready(item, name == 'Decided')}" for name, item in others
         if judge(unstated(item))[0] != "fail" and unready(item, name == "Decided")])

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
    return results


def landing(item):
    """(brief slot, value, label) for one Decided line, as the mapper places it.

    label is the slot or line label (goal, tools, write first, out of scope, ...), or None for any
    other line, which lands in Done. A `decide:` value is the Goal's decide item, with no prefix.
    """
    slot = slot_of(item)
    if slot:
        return BRIEF_SLOT[slot], slot_value(item), slot
    extra = extra_of(item)
    if extra:
        return BRIEF_SLOT[extra[0]], extra[1], extra[0]
    if OUT_OF_SCOPE.match(item.strip()):
        return "Constraints", scoped(item), "out of scope"
    return "Done", item.strip(), None


def asks(text):
    """(slot, value) for each Decided value that check_brief would ask a person about.

    Each Decided line is placed in its brief slot, with the Confirmed lines, and check_brief.asks
    judges them, so both checks ask the same question about the same value.
    """
    visible = split_fences(text.lstrip("\ufeff"))[0]
    sections = parse(visible)[0]
    lines = [f"- {slot}: {unstated(value)}" for slot, value, _ in map(landing, real_items(sections.get("Decided", [])))
             if value]
    lines += ["## Confirmed"] + [f"- {item}" for item in sections.get("Confirmed", [])]
    return brief_asks("\n".join(lines))


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
    asked = [] if failed else asks(text)
    lines += [f"ASK: {slot}: Is '{value}' a real answer for {slot}?" for slot, value in asked]
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
