"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions. Outcome asks them. It does not invent a tool, a role,
or a pass and fail case. write first is part of the Tools question until
the user answers.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import parse, real_items, slot_of, slot_value, split_fences  # noqa: E402

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
LATER = re.compile(r"\b(not now|later)\b", re.I)
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"


def items(text):
    visible, _, _ = split_fences(text)
    sections, _, _, _ = parse(visible)
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked")}


def slot_lines(rows, slot):
    return [row for row in rows if slot_of(row) == slot]


def question_of(row):
    text = (slot_value(row) if slot_of(row) else row).strip()
    text = re.sub(r"^(unknown:\s*)", "", text, flags=re.I)
    if not text.endswith("?"):
        text = text.rstrip(".") + "?"
    return text


def unknown(text):
    return f"unknown: {question_of(text)}"


def slot_text(decided, opens, slot, fallback):
    """A decided value, or an unknown from the open line, or the fallback question."""
    firm = slot_lines(decided, slot)
    if firm and slot_value(firm[0]):
        return slot_value(firm[0]), False
    pending = slot_lines(opens, slot)
    if pending:
        return unknown(pending[0]), True
    return unknown(fallback), True


def map_text(text):
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    other = [row for row in decided if slot_of(row) is None]
    goal, goal_unknown = slot_text(decided, opens, "goal", "What is the want?")
    done, done_unknown = slot_text(decided, opens, "done", "What does finished look like?")
    output, output_unknown = slot_text(decided, opens, "output", "What comes back?")
    verify, verify_unknown = slot_text(decided, opens, "verify", "How will you check it?")
    limits, limits_unknown = slot_text(decided, opens, "constraints", "What must the run not do?")
    decision = unknown(DECIDE)
    tools = unknown(TOOLS)
    agents = unknown(AGENTS)
    evals = unknown(EVALS)
    unknowns = [tools, agents, evals, decision]
    if goal_unknown:
        unknowns.append(goal)
    if done_unknown:
        unknowns.append(done)
    if output_unknown:
        unknowns.append(output)
    if verify_unknown:
        unknowns.append(verify)
    if limits_unknown:
        unknowns.append(limits)
    for row in opens:
        if slot_of(row):
            continue
        unknowns.append(unknown(row))
    lines = ["# Brief: from decisions", "", f"- Goal: {goal}", f"  - {decision}", "- Done:"]
    lines.append(f"  - {done}")
    for row in other:
        lines.append(f"  - {row}")
    lines.append(f"- Output: {output}")
    lines.append("- Constraints:")
    lines.append(f"  - {limits}")
    lines.append("  - Report only. Do not run or post until the user says to.")
    for row in parked:
        if LATER.search(row):
            lines.append(f"  - out of scope: {row}")
    lines.append("- Tools:")
    lines.append(f"  - {tools}")
    lines.append("- Agents and roles:")
    lines.append(f"  - {agents}")
    lines.append("- Evals:")
    lines.append(f"  - {evals}")
    lines.append("- Verification:")
    lines.append(f"  - {verify}")
    lines.append(f"  - {EVIDENCE}")
    if parked:
        lines.append("- Parking lot:")
        for row in parked:
            lines.append(f"  - {row}")
    lines.append("- Unknowns:")
    for item in unknowns:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("## Questions")
    lines.append("")
    for number, item in enumerate(unknowns[:3], 1):
        lines.append(f"{number}. {question_of(item)}")
    lines.append("")
    return "\n".join(lines)


def main(path):
    print(map_text(open(path, encoding="utf-8").read()))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(main(sys.argv[1]))
