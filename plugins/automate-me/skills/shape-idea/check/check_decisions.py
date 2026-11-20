"""Checks the shape of a decisions.md written by the shape-idea skill.

Usage: python3 check/check_decisions.py <decisions.md>

Sections are `## Decided`, `## Open`, `## Parked`, and `## Handoff`, in that order, each once.
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

Fails when:
- the file has no `# Decisions` title;
- a section is missing or repeated, or the four sections are out of order;
- an Open item does not end with exactly one `?`;
- a slot is missing from both Decided and Open, is repeated, is in both, or has an empty value;
- stop is missing, repeated, or not one of done, turn-cap, open-cap;
- stop does not match the file (done, open-cap, or turn-cap rules above);
- turns is missing, repeated, or not a whole number from 1 through 10;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line;
- Handoff has no single `writing: pass` line;
- the shared writing check fails.

Prints a PASS or FAIL line per check and exits 1 on any FAIL.
Exit 0 when every check passed. Exit 2 on a usage error.
"""
import contextlib
import io
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared")))
from check_writing import check_writing  # noqa: E402

SECTIONS = ["Decided", "Open", "Parked", "Handoff"]
HEAD = re.compile(r"^##\s+(Decided|Open|Parked|Handoff)\s*$", re.I)
BULLET = re.compile(r"^[-*]\s+(.*)$")
STOPS = {"done", "turn-cap", "open-cap"}
NEXT = "next: /automate-me:outcome"
TITLE = re.compile(r"^# Decisions\b", re.M)
MAX_TURNS = 10
OPEN_CAP = 5
SLOTS = ["goal", "done", "output", "verify", "constraints"]
SLOT_LINE = {slot: re.compile(rf"^{slot}:(.*)$", re.I) for slot in SLOTS}
ASCII_DIGITS = re.compile(r"^[0-9]+$")


def canon(name):
    return next(s for s in SECTIONS if s.lower() == name.lower())


def is_none(item):
    return item.strip().rstrip(".").lower() == "none"


def real_items(items):
    """A lone `none` means the section is empty."""
    if len(items) == 1 and is_none(items[0]):
        return []
    return items


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


def slot_value(item):
    """The text after `<slot>:` when item is a slot line, else None."""
    for pattern in SLOT_LINE.values():
        match = pattern.match(item)
        if match:
            return match.group(1).strip()
    return None


def slot_of(item):
    for slot, pattern in SLOT_LINE.items():
        if pattern.match(item):
            return slot
    return None


def is_slot_line(item):
    return slot_of(item) is not None


def has_slot(items, slot):
    return any(SLOT_LINE[slot].match(item) for item in items)


def field(items, label):
    """Values of Handoff bullets that start with `label:`."""
    found = []
    for item in items:
        match = re.match(rf"^{re.escape(label)}:\s*(.*?)\s*$", item, re.I)
        if match:
            found.append(match.group(1).strip())
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
    sections, counts, positions, extras = parse(text)
    results = []

    def add(name, fails):
        results.append((name, fails))

    add("file has a Decisions title", [] if TITLE.search(text) else ["missing a `# Decisions` title"])

    present = []
    for name in SECTIONS:
        n = counts.get(name, 0)
        if n == 0:
            present.append(f"missing section: {name}")
        elif n != 1:
            present.append(f"section {name} appears {n} times")
    add("sections present once", present)

    order = []
    if all(counts.get(name) == 1 for name in SECTIONS) and positions != SECTIONS:
        order.append("sections are " + ", ".join(positions) + "; use Decided, Open, Parked, Handoff")
    add("sections in order", order)

    decided = real_items(sections.get("Decided", []))
    opens = real_items(sections.get("Open", []))
    q_fails = []
    for item in opens:
        if item.count("?") != 1 or not item.endswith("?"):
            q_fails.append(f"open item needs one question at the end: {item!r}")
    add("every open item ends with a question", q_fails)
    add("every slot is decided or open",
        [f"missing slot: {slot}. Add a Decided `{slot}:` line or an Open `{slot}: ...?` item"
         for slot in SLOTS if not has_slot(decided, slot) and not has_slot(opens, slot)])

    dup_fails = []
    both_fails = []
    empty_fails = []
    for slot in SLOTS:
        in_decided = [item for item in decided if SLOT_LINE[slot].match(item)]
        in_open = [item for item in opens if SLOT_LINE[slot].match(item)]
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

    handoff = sections.get("Handoff", [])
    handoff_ready = counts.get("Handoff") == 1
    stops = field(handoff, "stop") if handoff_ready else []
    stop_fails = []
    if handoff_ready and len(stops) == 0:
        stop_fails.append("stop line is missing; write stop: done, stop: turn-cap, or stop: open-cap")
    elif len(stops) > 1:
        stop_fails.append(f"stop appears {len(stops)} times")
    elif stops and stops[0].lower() not in STOPS:
        stop_fails.append(f"stop is {stops[0]!r}; use done, turn-cap, or open-cap")
    add("stop reason is done, turn-cap, or open-cap", stop_fails)

    turns = field(handoff, "turns") if handoff_ready else []
    turn_fails = []
    turn_number = None
    if handoff_ready and len(turns) == 0:
        turn_fails.append("turn count is missing; write turns: <n> in Handoff")
    elif len(turns) > 1:
        turn_fails.append(f"turn count appears {len(turns)} times")
    elif turns and not ASCII_DIGITS.fullmatch(turns[0]):
        turn_fails.append(f"turns is {turns[0]!r}; write a whole number from 1 through {MAX_TURNS}")
    elif turns:
        turn_number = int(turns[0])
        if turn_number < 1 or turn_number > MAX_TURNS:
            turn_fails.append(f"turns is {turn_number}, write a whole number from 1 through {MAX_TURNS}")
    add("turn count recorded and at most 10", turn_fails)

    stop = stops[0].lower() if len(stops) == 1 and stops[0].lower() in STOPS else None
    non_slot = [item for item in opens if not is_slot_line(item)]
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

    add("no item longer than one line",
        [f"{name}: extra line {text!r}. Each item stays on one line" for name, text in extras])

    next_fails = []
    if handoff_ready and not any(item.strip().lower() == NEXT for item in handoff):
        next_fails.append(f"Handoff has no `{NEXT}` line")
    add("handoff names outcome", next_fails)

    writing = field(handoff, "writing") if handoff_ready else []
    writing_fails = []
    if handoff_ready and writing != ["pass"]:
        writing_fails.append("Handoff has no single `writing: pass` line. Run the shared writing check first")
    add("handoff says writing pass", writing_fails)
    add("prose passes the writing check", prose_fails(text))
    return results


def main(path):
    failed = False
    for name, fails in check(open(path).read()):
        print(f"{'FAIL' if fails else 'PASS'} {name}")
        for fail in fails:
            print(f"  {fail}")
        failed = failed or bool(fails)
    print(f"{'FAIL' if failed else 'PASS'} decisions: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) == 2 else 2)
    sys.exit(main(sys.argv[1]))
