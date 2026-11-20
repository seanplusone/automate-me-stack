"""Checks the shape of a decisions.md written by the shape-idea skill.

Usage: python3 check/check_decisions.py <decisions.md>

Sections are `## Decided`, `## Open`, `## Parked`, and `## Handoff`, in that order, each once.
An item is one top-level bullet (`- ` or `* `). A later physical line under a section is an item
that ran past one line. A section whose only item is `none` has no items. Handoff holds:

    - next: /automate-me:outcome
    - stop: done | turn-cap | open-cap
    - turns: <n>

Fails when:
- a section is missing or repeated, or the four sections are out of order;
- an Open item does not end with `?`;
- Open has more than 5 items;
- stop is missing, repeated, or not one of done, turn-cap, open-cap;
- turns is missing, repeated, not a whole number, or greater than 10;
- stop is done and Decided has no line starting with `goal:` or no line starting with `done:`;
- any item runs past one line;
- Handoff has no `next: /automate-me:outcome` line.

Prints a PASS or FAIL line per check and exits 1 on any FAIL.
Exit 0 when every check passed. Exit 2 on a usage error.
"""
import re
import sys

SECTIONS = ["Decided", "Open", "Parked", "Handoff"]
HEAD = re.compile(r"^##\s+(Decided|Open|Parked|Handoff)\s*$", re.I)
BULLET = re.compile(r"^[-*]\s+(.*)$")
STOPS = {"done", "turn-cap", "open-cap"}
NEXT = "next: /automate-me:outcome"
MAX_TURNS = 10
MAX_OPEN = 5
PREFIX = {"goal": re.compile(r"^goal:", re.I), "done": re.compile(r"^done:", re.I)}


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


def field(items, label):
    """Values of Handoff bullets that start with `label:`."""
    found = []
    for item in items:
        match = re.match(rf"^{re.escape(label)}:\s*(\S+)\s*$", item, re.I)
        if match:
            found.append(match.group(1))
    return found


def check(text):
    sections, counts, positions, extras = parse(text)
    results = []

    def add(name, fails):
        results.append((name, fails))

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

    opens = real_items(sections.get("Open", []))
    add("every open item ends with a question",
        [f"open item does not end with ?: {item!r}" for item in opens if not item.endswith("?")])
    add("at most 5 open items",
        [f"{len(opens)} open items, at most {MAX_OPEN}"] if len(opens) > MAX_OPEN else [])

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
    if handoff_ready and len(turns) == 0:
        turn_fails.append("turn count is missing; write turns: <n> in Handoff")
    elif len(turns) > 1:
        turn_fails.append(f"turn count appears {len(turns)} times")
    elif turns and not turns[0].isdigit():
        turn_fails.append(f"turns is {turns[0]!r}; write a whole number from 0 through {MAX_TURNS}")
    elif turns and int(turns[0]) > MAX_TURNS:
        turn_fails.append(f"turns is {int(turns[0])}, at most {MAX_TURNS}")
    add("turn count recorded and at most 10", turn_fails)

    done_fails = []
    if len(stops) == 1 and stops[0].lower() == "done":
        decided = real_items(sections.get("Decided", []))
        if not any(PREFIX["goal"].match(item) for item in decided):
            done_fails.append("Decided has no goal: line")
        if not any(PREFIX["done"].match(item) for item in decided):
            done_fails.append("Decided has no done: line")
    add("stop done has goal and done", done_fails)

    add("no item longer than one line",
        [f"{name}: extra line {text!r}. Each item stays on one line" for name, text in extras])

    next_fails = []
    if handoff_ready and not any(item.strip().lower() == NEXT for item in handoff):
        next_fails.append(f"Handoff has no `{NEXT}` line")
    add("handoff names outcome", next_fails)
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
