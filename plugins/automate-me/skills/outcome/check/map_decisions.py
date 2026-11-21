"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
The script runs check_decisions, which checks the file's shape, maps it with map_text(), and runs
check_brief's check() and asks() on that brief. A file that fails exits 1, and a file with a value
to confirm exits 2 with its ASK lines. Neither prints a brief. On exit 0 it prints the brief
check_brief passed, so the mapper and check_brief always agree.

Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions, unless a Decided line already names that slot. Goal holds only the
user's lines. The decide question, stock or Open, goes to Unknowns unless a Decided `decide:` line answers it.
An Open `tools:`, `agents:`, `evals:` or `decide:` question replaces that stock question.
Outcome asks them. It does not invent a tool, a role, or a pass and fail case.
A Decided `write first:` line goes under Tools. Each Decided line lands where
check_decisions.landing() says. A Parked line stays in the Parking lot. An `out of scope:` tag,
bold or not, also puts it in Constraints, unless it is a question. No other word moves it.
Bad arguments, or a path that cannot be read, exit 3 with one line on stderr.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import (  # noqa: E402
    bare,
    ends_in_question,
    extra_of,
    landing,
    parked_limit,
    parse,
    question_end,
    read,
    real_items,
    report,
    scoped,
    slot_of,
    slot_value,
    split_fences,
    unreadable,
    unstated,
)

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
REPORT = "Report only. Do not run or post until the user says to."
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"
ASKED = ("decide", "tools", "agents", "evals")
# A brief tag and the one brief slot where it may lead an item.
TAG_LEAD = re.compile(r"^(investigate|out of scope|how)\s*[:\uff1a]", re.I)
TAG_HOME = {"investigate": "Done", "out of scope": "Constraints", "how": "Agents and roles"}
DEFAULT_LEAD = re.compile(r"^default\b", re.I)


def items(text):
    visible = split_fences(text.lstrip("\ufeff"))[0]
    sections = parse(visible)[0]
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked", "Confirmed")}


def slot_lines(rows, slot):
    return [row for row in rows if slot_of(row) == slot]


def question_of(row):
    extra = extra_of(row)
    text = (slot_value(row) if slot_of(row) else extra[1] if extra else row).strip()
    text = re.sub(r"^(unknown:\s*)", "", text, flags=re.I)
    text = re.sub(r"^(stated:\s*)", "", text, flags=re.I)
    end = question_end(text)
    # check_brief reads only an ASCII `?`, so the mark that ends the question is written as one.
    return text.rstrip(".") + "?" if end is None else text[:end] + "?" + text[end + 1:]


def unknown(text):
    return f"unknown: {question_of(text)}"


def brief_item(text, slot):
    """A line that is not a slot, as written in brief slot `slot` (Done or Parking lot), without its `stated:` labels.

    When it starts with a brief tag outside its home, or with `default`, one `stated:` goes in front so check_brief
    reads it as words. check_decisions judges it again without that prefix.
    """
    raw = unstated(text)
    tag = TAG_LEAD.match(raw)
    if (tag and TAG_HOME[tag.group(1).lower()] != slot) or DEFAULT_LEAD.match(raw):
        return f"stated: {raw}"
    return raw


def slot_text(decided, opens, slot, fallback):
    """Return (text, is_unknown)."""
    firm = slot_lines(decided, slot)
    if firm:
        return unstated(slot_value(firm[0])), False
    pending = slot_lines(opens, slot)
    return unknown(pending[0] if pending else fallback), True


def map_text(text):
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    lands = [landing(row) for row in decided]
    named = {label: value for _, value, label in lands if label in ASKED + ("write first",) and bare(value)}
    limits_out = [value for _, value, label in lands if label == "out of scope"]
    limits_out += [scoped(row) for row in parked if parked_limit(row)]
    other = [value for _, value, label in lands if label is None]
    # An Open tools:, agents:, evals: or decide: question asks for that slot, in place of the stock question.
    asked, rest = {}, []
    for row in opens:
        name = (extra_of(row) or (None,))[0]
        if name in ASKED and name not in named and name not in asked:
            asked[name] = unknown(row)
        elif not slot_of(row):
            rest.append(unknown(row))
    goal, goal_unknown = slot_text(decided, opens, "goal", "What is the want?")
    done, done_unknown = slot_text(decided, opens, "done", "What does finished look like?")
    output, output_unknown = slot_text(decided, opens, "output", "What comes back?")
    verify, verify_unknown = slot_text(decided, opens, "verify", "How will you check it?")
    limits, limits_unknown = slot_text(decided, opens, "constraints", "What must the run not do?")
    stock = {"decide": DECIDE, "tools": TOOLS, "agents": AGENTS, "evals": EVALS}
    question = {name: asked.get(name) or unknown(stock[name]) for name in ASKED if name not in named}
    # Read-back order: open goal or done, then the decide question,
    # then Tools, Agents and roles, and Evals. The rest stay listed.
    ordered = [goal] * goal_unknown + [done] * done_unknown
    ordered += [question[name] for name in ASKED if name in question]
    ordered += [output] * output_unknown + [verify] * verify_unknown + [limits] * limits_unknown + rest
    ordered += [unknown(row) for row in parked if ends_in_question(row)]
    lines = ["# Brief: from decisions", ""]
    lines.append(f"- Goal: {goal}")
    # Goal holds only the user's lines. The stock or Open decide question waits in Unknowns, so no line the mapper
    # adds sits beside the user's goal.
    lines += [f"  - {brief_item(named['decide'], 'Goal')}"] if "decide" in named else []
    lines.append("- Done:")
    lines.append(f"  - {done}")
    lines += [f"  - {brief_item(row, 'Done')}" for row in other]
    lines.append(f"- Output: {output}")
    lines.append("- Constraints:")
    lines.append(f"  - {limits}")
    lines.append(f"  - {REPORT}")
    lines += [f"  - {row}" for row in limits_out]
    for slot, name in (("Tools", "tools"), ("Agents and roles", "agents"), ("Evals", "evals")):
        lines += [f"- {slot}: {named[name]}"] if name in named else [f"- {slot}:", f"  - {question[name]}"]
        if name == "tools" and "write first" in named:
            lines.append(f"  - write first: {named['write first']}")
    lines.append("- Verification:")
    lines.append(f"  - {verify}")
    lines.append(f"  - {EVIDENCE}")
    if parked:
        lines.append("- Parking lot:")
        lines += [f"  - {brief_item(row, 'Parking lot')}" for row in parked]
    if ordered:
        lines.append("- Unknowns:")
        lines += [f"  - {item}" for item in ordered]
        lines += ["", "## Questions", ""]
        lines += [f"{number}. {question_of(item)}" for number, item in enumerate(ordered[:3], 1)]
    if found["Confirmed"]:
        lines += ["", "## Confirmed", ""] + [f"- {row}" for row in found["Confirmed"]]
    return "\n".join(lines) + "\n"


def main(path):
    text, why = read(path)
    if why:
        return unreadable(path, why)
    code, lines = report(text, path)
    if code:
        print("\n".join(lines))
        return code
    print(map_text(text), end="")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__.strip())
        sys.exit(0)
    if len(sys.argv) != 2:
        print("usage: python3 check/map_decisions.py <decisions.md>", file=sys.stderr)
        sys.exit(3)
    sys.exit(main(sys.argv[1]))
