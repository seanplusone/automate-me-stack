"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
The script runs check_decisions first. A file that fails that check exits 1
and prints those failures. It does not print a brief.

Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions, unless a Decided line already names that slot.
Outcome asks them. It does not invent a tool, a role, or a pass and fail case.
write first is part of the Tools question until the user answers.

A placeholder slot is left as the user's placeholder. The decide question,
"Report only", and the evidence sentence are not added beside it, so the
brief check still flags that slot.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import (  # noqa: E402
    check as check_decisions,
    extra_of,
    parse,
    placeholder_value,
    real_items,
    slot_of,
    slot_value,
    split_fences,
)

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check")))
from check_brief import is_bare_trap  # noqa: E402

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
REPORT = "Report only. Do not run or post until the user says to."
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"
DECISION_WORD = re.compile(r"\b(decide|decides|decision)\b", re.I)
HEDGE = re.compile(r"\b(maybe|not sure)\b", re.I)
NOT_NOW = re.compile(r"\bnot now\b", re.I)
NO_LATER = re.compile(r"\bno later\b", re.I)
LATER = re.compile(r"\blater\b", re.I)
TAG_START = re.compile(r"^(investigate|out of scope|how)\s*:", re.I)
UNKNOWN_START = re.compile(r"^unknown\b", re.I)
DEFAULT_START = re.compile(r"^default\b", re.I)
# Where a leading tag is legal. Anywhere else, prefix the line so the tag
# is no longer the first words. The user's words stay after the prefix.
TAG_HOME = {
    "Done": {"investigate"},
    "Constraints": {"out of scope"},
    "Agents and roles": {"how"},
}


def items(text):
    visible, _, _ = split_fences(text)
    sections, _, _, _ = parse(visible)
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked")}


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


def names_decision(rows):
    """A Decided line already names the decision when it says decide or decision."""
    return any(DECISION_WORD.search(row) and not row.rstrip().endswith("?") for row in rows)


def standalone_later(row):
    """Not now, or later on its own. Not a question, a hedge, or 'no later than'."""
    text = row.strip()
    if text.endswith("?") or HEDGE.search(text):
        return False
    if NOT_NOW.search(text):
        return True
    return bool(LATER.search(NO_LATER.sub("", text)))


def safe_item(text, slot):
    """Prefix a line whose first words would trip a brief tag. Keep the words."""
    raw = text.strip()
    home = TAG_HOME.get(slot, set())
    tag = TAG_START.match(raw)
    if tag and tag.group(1).lower() not in home:
        return f"stated: {raw}"
    if UNKNOWN_START.match(raw) or DEFAULT_START.match(raw) or is_bare_trap(raw):
        return f"stated: {raw}"
    return raw


def slot_text(decided, opens, slot, fallback):
    """Return (text, is_unknown, is_placeholder)."""
    firm = slot_lines(decided, slot)
    if firm and slot_value(firm[0]):
        value = slot_value(firm[0])
        return value, False, placeholder_value(value) or value.strip().endswith("?")
    pending = slot_lines(opens, slot)
    if pending:
        return unknown(pending[0]), True, False
    return unknown(fallback), True, False


def map_text(text):
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    extras = {}
    other = []
    for row in decided:
        if slot_of(row):
            continue
        got = extra_of(row)
        if got:
            extras[got[0]] = got[1]
            continue
        other.append(row)
    goal, goal_unknown, goal_ph = slot_text(decided, opens, "goal", "What is the want?")
    done, done_unknown, done_ph = slot_text(decided, opens, "done", "What does finished look like?")
    output, output_unknown, _ = slot_text(decided, opens, "output", "What comes back?")
    verify, verify_unknown, verify_ph = slot_text(decided, opens, "verify", "How will you check it?")
    limits, limits_unknown, limits_ph = slot_text(decided, opens, "constraints", "What must the run not do?")
    add_decision = not names_decision(decided)
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
    goal_text = goal if goal_unknown or goal_ph else safe_item(goal, "Goal")
    lines.append(f"- Goal: {goal_text}")
    if add_decision and not goal_ph:
        lines.append(f"  - {decision}")
    lines.append("- Done:")
    done_text = done if done_unknown or done_ph else safe_item(done, "Done")
    lines.append(f"  - {done_text}")
    if not done_ph:
        for row in other:
            lines.append(f"  - {safe_item(row, 'Done')}")
    output_text = output if output_unknown else safe_item(output, "Output")
    lines.append(f"- Output: {output_text}")
    lines.append("- Constraints:")
    limits_text = limits if limits_unknown or limits_ph else safe_item(limits, "Constraints")
    lines.append(f"  - {limits_text}")
    if not limits_ph:
        lines.append(f"  - {REPORT}")
        for row in parked:
            if standalone_later(row):
                lines.append(f"  - out of scope: {row.strip()}")
    if "tools" in extras:
        lines.append(f"- Tools: {safe_item(extras['tools'], 'Tools')}")
    else:
        lines.append("- Tools:")
        lines.append(f"  - {tools}")
    if "agents" in extras:
        lines.append(f"- Agents and roles: {safe_item(extras['agents'], 'Agents and roles')}")
    else:
        lines.append("- Agents and roles:")
        lines.append(f"  - {agents}")
    if "evals" in extras:
        lines.append(f"- Evals: {safe_item(extras['evals'], 'Evals')}")
    else:
        lines.append("- Evals:")
        lines.append(f"  - {evals}")
    lines.append("- Verification:")
    verify_text = verify if verify_unknown or verify_ph else safe_item(verify, "Verification")
    lines.append(f"  - {verify_text}")
    if not verify_ph:
        lines.append(f"  - {EVIDENCE}")
    if parked:
        lines.append("- Parking lot:")
        for row in parked:
            lines.append(f"  - {safe_item(row, 'Parking lot')}")
    if ordered:
        lines.append("- Unknowns:")
        for item in ordered:
            lines.append(f"  - {item}")
        lines.append("")
        lines.append("## Questions")
        lines.append("")
        for number, item in enumerate(ordered[:3], 1):
            lines.append(f"{number}. {question_of(item)}")
    lines.append("")
    return "\n".join(lines)


def failures(text):
    """The check_decisions report. Empty when the file passes."""
    lines = []
    failed = False
    for name, fails in check_decisions(text):
        lines.append(f"{'FAIL' if fails else 'PASS'} {name}")
        for fail in fails:
            lines.append(f"  {fail}")
        failed = failed or bool(fails)
    return failed, "\n".join(lines)


def main(path):
    try:
        text = open(path, encoding="utf-8").read()
    except UnicodeDecodeError:
        print("FAIL file is not UTF-8")
        print(f"FAIL decisions: {path}")
        return 1
    failed, report = failures(text)
    if failed:
        print(report)
        print(f"FAIL decisions: {path}")
        return 1
    print(map_text(text))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 2)
    sys.exit(main(sys.argv[1]))
