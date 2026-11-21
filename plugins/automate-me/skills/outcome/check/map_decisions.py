"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
The script runs check_decisions first. A file that fails that check exits 1,
and a file with a value to confirm exits 2 with its ASK lines. Neither prints a brief.

Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions, unless a Decided line already names that slot.
Outcome asks them. It does not invent a tool, a role, or a pass and fail case.
write first is part of the Tools question until the user answers.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import (  # noqa: E402
    OUT_OF_SCOPE,
    brief_item,
    extra_of,
    parse,
    read,
    real_items,
    report,
    slot_of,
    slot_value,
    split_fences,
)

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check")))
from check_brief import classify  # noqa: E402

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
REPORT = "Report only. Do not run or post until the user says to."
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"
HEDGE = re.compile(r"\b(maybe|not sure|i think)\b", re.I)
NOT_NOW = re.compile(r"\bnot now\b", re.I)
NO_LATER = re.compile(r"\bnot? later\b", re.I)
LATER = re.compile(r"\blater\b", re.I)
QUOTED = re.compile(r"\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d")
def items(text):
    visible = split_fences(text.lstrip("\ufeff"))[0]
    sections = parse(visible)[0]
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked", "Confirmed")}


def slot_lines(rows, slot):
    return [row for row in rows if slot_of(row) == slot]


def question_of(row):
    text = (slot_value(row) if slot_of(row) else row).strip()
    text = re.sub(r"^(unknown:\s*)", "", text, flags=re.I)
    text = re.sub(r"^(stated:\s*)", "", text, flags=re.I)
    if not text.endswith("?"):
        text = text.rstrip(".") + "?"
    return text


def unknown(text):
    return f"unknown: {question_of(text)}"


def standalone_later(row):
    """Not now, or later on its own. Not a question, a hedged later, 'no later than', or a quoted later."""
    text = QUOTED.sub("", row.strip())
    if row.strip().endswith("?"):
        return False
    if NOT_NOW.search(text):
        return True
    return not HEDGE.search(text) and bool(LATER.search(NO_LATER.sub("", text))) and classify(row) == "pass"


def slot_text(decided, opens, slot, fallback):
    """Return (text, is_unknown)."""
    firm = slot_lines(decided, slot)
    if firm:
        return slot_value(firm[0]), False
    pending = slot_lines(opens, slot)
    return unknown(pending[0] if pending else fallback), True


def map_text(text):
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    extras, scoped, other = {}, [], []
    for row in decided:
        if slot_of(row):
            continue
        got = extra_of(row)
        if got:
            extras[got[0]] = got[1]
        elif OUT_OF_SCOPE.match(row.strip()):
            scoped.append(row.strip())
        else:
            other.append(row)
    goal, goal_unknown = slot_text(decided, opens, "goal", "What is the want?")
    done, done_unknown = slot_text(decided, opens, "done", "What does finished look like?")
    output, output_unknown = slot_text(decided, opens, "output", "What comes back?")
    verify, verify_unknown = slot_text(decided, opens, "verify", "How will you check it?")
    limits, limits_unknown = slot_text(decided, opens, "constraints", "What must the run not do?")
    add_decision = "decide" not in extras
    decision = unknown(DECIDE)
    tools = unknown(TOOLS)
    agents = unknown(AGENTS)
    evals = unknown(EVALS)
    # Read-back order: open goal or done, then the decide question,
    # then Tools, Agents and roles, and Evals. The rest stay listed.
    ordered = []
    if goal_unknown:
        ordered.append(goal)
    if done_unknown:
        ordered.append(done)
    if add_decision:
        ordered.append(decision)
    if "tools" not in extras:
        ordered.append(tools)
    if "agents" not in extras:
        ordered.append(agents)
    if "evals" not in extras:
        ordered.append(evals)
    if output_unknown:
        ordered.append(output)
    if verify_unknown:
        ordered.append(verify)
    if limits_unknown:
        ordered.append(limits)
    for row in opens:
        if slot_of(row):
            continue
        ordered.append(unknown(row))
    for row in parked:
        if row.strip().endswith("?"):
            ordered.append(unknown(row))
    lines = ["# Brief: from decisions", ""]
    lines.append(f"- Goal: {goal}")
    lines.append(f"  - {decision}" if add_decision else f"  - decide: {extras['decide']}")
    lines.append("- Done:")
    lines.append(f"  - {done}")
    for row in other:
        lines.append(f"  - {brief_item(row, 'Done')}")
    lines.append(f"- Output: {output}")
    lines.append("- Constraints:")
    lines.append(f"  - {limits}")
    lines.append(f"  - {REPORT}")
    for row in scoped:
        lines.append(f"  - {row}")
    for row in parked:
        if standalone_later(row):
            lines.append(f"  - out of scope: {row.strip()}")
    for slot, name, question in (("Tools", "tools", tools), ("Agents and roles", "agents", agents),
                                 ("Evals", "evals", evals)):
        if name in extras:
            lines.append(f"- {slot}: {extras[name]}")
        else:
            lines.append(f"- {slot}:")
            lines.append(f"  - {question}")
    lines.append("- Verification:")
    lines.append(f"  - {verify}")
    lines.append(f"  - {EVIDENCE}")
    if parked:
        lines.append("- Parking lot:")
        for row in parked:
            lines.append(f"  - {brief_item(row, 'Parking lot')}")
    if ordered:
        lines.append("- Unknowns:")
        for item in ordered:
            lines.append(f"  - {item}")
        lines.append("")
        lines.append("## Questions")
        lines.append("")
        for number, item in enumerate(ordered[:3], 1):
            lines.append(f"{number}. {question_of(item)}")
    if found["Confirmed"]:
        lines += ["", "## Confirmed", ""] + [f"- {row}" for row in found["Confirmed"]]
    return "\n".join(lines) + "\n"


def main(path):
    text = read(path)
    code, lines = report(text, path)
    if code:
        print("\n".join(lines))
        return code
    print(map_text(text), end="")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 3)
    sys.exit(main(sys.argv[1]))
