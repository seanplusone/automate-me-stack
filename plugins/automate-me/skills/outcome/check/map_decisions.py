"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
The script runs check_decisions first. A file that fails that check exits 1,
and a file with a value to confirm exits 2 with its ASK lines. Neither prints a brief.

Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions, unless a Decided line already names that slot.
An Open `tools:`, `agents:`, `evals:` or `decide:` question replaces that stock question.
Outcome asks them. It does not invent a tool, a role, or a pass and fail case.
A Decided `write first:` line goes under Tools. Each Decided line lands where
check_decisions.landing() says, so the check and the mapper judge the same value.
A path that cannot be read exits 3 with one line.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import (  # noqa: E402
    OUT_OF_SCOPE,
    brief_item,
    extra_of,
    landing,
    parse,
    read,
    real_items,
    report,
    scoped,
    slot_of,
    slot_value,
    split_fences,
    unreadable,
)

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check")))
from check_brief import classify  # noqa: E402

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
REPORT = "Report only. Do not run or post until the user says to."
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"
HEDGE = re.compile(r"\b(maybe|perhaps|possibly|probably|not sure|unsure|i think)\b", re.I)
NOT_NOW = re.compile(r"\bnot now$", re.I)
FOR_LATER = re.compile(r"(?:,\s*|\bfor\s+)later$", re.I)
QUOTED = re.compile(r"\"[^\"\n]*\"|\u201c[^\u201d\n]*\u201d")
ASKED = ("decide", "tools", "agents", "evals")
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
    if not text.endswith("?"):
        text = text.rstrip(".") + "?"
    return text


def unknown(text):
    return f"unknown: {question_of(text)}"


def deferred(row):
    """A Parked line that ends in a bare deferral: not now, `, later`, or `for later`. Hedged or quoted, it stays parked."""
    text = QUOTED.sub("", row.strip()).rstrip(" .!")
    if text.endswith("?") or classify(row) != "pass":
        return False
    return bool(NOT_NOW.search(text)) or (bool(FOR_LATER.search(text)) and not HEDGE.search(text))


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
    lands = [landing(row) for row in decided]
    named = {label: value for _, value, label in lands if label in ASKED + ("write first",)}
    limits_out = [value for _, value, label in lands if label == "out of scope"]
    limits_out += [scoped(row) if OUT_OF_SCOPE.match(row.strip()) else f"out of scope: {row.strip()}"
                   for row in parked if OUT_OF_SCOPE.match(row.strip()) or deferred(row)]
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
    ordered += [unknown(row) for row in parked if row.strip().endswith("?")]
    lines = ["# Brief: from decisions", ""]
    lines.append(f"- Goal: {goal}")
    lines.append(f"  - {named.get('decide') or question['decide']}")
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
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0 if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help") else 3)
    sys.exit(main(sys.argv[1]))
