"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md>

This is the literal mapping in ../SKILL.md, "A decisions file".
Plan first is the agent's call: none needed. Decision, Context, and Taste
are filled from a non-slot line when one is labeled, and otherwise marked unknown.
A parked line that says "not now" or "later" is also an out-of-scope must-have.
An open slot fills that brief slot with unknown, and the same question is listed
under Unknowns.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import parse, real_items, slot_of, slot_value, split_fences  # noqa: E402

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
LATER = re.compile(r"\b(not now|later)\b", re.I)


def items(text):
    visible, _, _ = split_fences(text)
    sections, _, _, _ = parse(visible)
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked")}


def slot_lines(rows, slot):
    return [row for row in rows if slot_of(row) == slot]


def question_of(row):
    text = (slot_value(row) or row).strip()
    text = re.sub(r"^(unknown:\s*)", "", text, flags=re.I)
    if not text.endswith("?"):
        text = text.rstrip(".") + "?"
    return text


def unknown(text):
    return f"unknown: {question_of(text)}"


def map_text(text):
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    other = [row for row in decided if slot_of(row) is None]
    goal = slot_lines(decided, "goal")
    output = slot_lines(decided, "output") or slot_lines(opens, "output")
    verify = slot_lines(decided, "verify") or slot_lines(opens, "verify")
    output_open = bool(slot_lines(opens, "output")) and not slot_lines(decided, "output")
    verify_open = bool(slot_lines(opens, "verify")) and not slot_lines(decided, "verify")
    must = []
    for slot in ("done", "constraints"):
        for row in slot_lines(decided, slot):
            must.append(slot_value(row))
    must.extend(other)
    for row in parked:
        if LATER.search(row):
            must.append(f"out of scope: {row}")
    unknowns = []
    if not other:
        context = unknown("What already exists?")
        unknowns.append(context)
    else:
        context = " ".join(other)
    decision = unknown("What will you decide with the result?")
    taste = unknown("What should be flagged but not required?")
    unknowns.extend([decision, taste])
    if output_open:
        output_line = unknown(output[0])
        unknowns.append(output_line)
    else:
        output_line = slot_value(output[0]) if output else unknown("What comes back?")
        if output_line.startswith("unknown:"):
            unknowns.append(output_line)
    if verify_open:
        verify_line = unknown(verify[0])
        unknowns.append(verify_line)
    else:
        verify_line = slot_value(verify[0]) if verify else unknown("How will you check it?")
        if str(verify_line).startswith("unknown:"):
            unknowns.append(verify_line)
    lines = [
        "# Brief: from decisions",
        "",
        "- Plan first: none needed",
        f"- Goal: {slot_value(goal[0]) if goal else unknown('What is the want?')}",
        f"- Decision: {decision}",
        f"- Context: {context}",
        "- Must-haves:",
    ]
    for item in must or ["unknown: What must the result include?"]:
        lines.append(f"  - {item}")
    lines.append(f"- Taste: {taste}")
    lines.append(f"- Output: {output_line}")
    lines.append("- Verify:")
    lines.append(f"  - {verify_line}")
    lines.append(f"  - {EVIDENCE}")
    lines.append("- If stuck: Report only. Do not guess an unknown. Stop and ask.")
    lines.append("- Skills: none")
    lines.append("- Parking lot: " + (" ".join(parked) if parked else "none"))
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
