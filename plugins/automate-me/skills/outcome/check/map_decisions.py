"""Map a shape-idea decisions.md into an outcome brief.

Usage: python3 check/map_decisions.py <decisions.md> [--confirmed <confirmed.md>]

This is the literal mapping in ../SKILL.md, "A decisions file".
The script runs check_decisions first, with the same confirmed.md. A file that is format invalid exits 1, and a file
with a CHECK WITH ME list exits 2. Both print the checker's report and no brief. On exit 0 it prints the brief, and
check_decisions has already run check_brief on that brief, so the brief passes it.

Shape-idea records goal, done, output, constraints, and verify.
Tools, Agents and roles, and Evals are not asked there. They are written
as unknown questions, unless a Decided line already names that slot. Goal holds only the
user's lines. The decide question, stock or Open, goes to Unknowns unless a Decided `decide:` line answers it.
An Open `tools:`, `agents:`, `evals:` or `decide:` question replaces that stock question.
Outcome asks them. It does not invent a tool, a role, or a pass and fail case.
A Decided `write first:` line goes under Tools. Each Decided line lands where
check_decisions.landing() says. A Parked line stays in the Parking lot. An `out of scope:` tag,
bold or not, also puts it in Constraints, unless it has a question mark. Then it is a question in Unknowns.
Each confirmed value is copied into the brief's `## Confirmed` block.

check_brief fails an `[insert ...]` anywhere and an Evals case body that is a placeholder, and a `## Confirmed` line
does not clear a fail. check_decisions lists such text inside a longer value for a yes, so the mapper writes it the way
check_brief reads as literal: an `[insert ...]` goes in a code span, and `stated: ` goes before a case body such as
`` `N/A` `` that holds a code span.

A value check_brief would read as a marker gets `stated: ` in front, so check_brief reads it as the person's words:
a brief tag outside its home slot (`how:` in Done), `default` on a line that is not a slot's own value, `unknown` at
the start, only trap words, or `none`. check_decisions has judged the value itself, and a confirmation is the yes.
Bad arguments, or a path that cannot be read, exit 3 with one line on stderr.
"""
import os
import re
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shape-idea", "check")))
from check_decisions import (  # noqa: E402
    BRIEF_SLOT,
    arguments,
    blank,
    extra_of,
    has_question,
    inputs,
    landing,
    parked_limit,
    parse,
    real_items,
    report,
    scoped,
    slot_of,
    slot_value,
    split_fences,
    unstated,
    utf8_output,
)
from check_brief import (  # noqa: E402
    CODE_SPAN,
    INSERT_FINDER,
    TAG,
    TAGS,
    UNKNOWN_START,
    case_marks,
    classify,
    is_bare_trap,
    judge,
)

EVIDENCE = "Every claim names its run, file:line or photo, or says guess."
REPORT = "Report only. Do not run or post until the user says to."
TOOLS = "Which tool must the run use, and what, if anything, must be written first?"
AGENTS = "Who does the work, and does anyone else check it?"
EVALS = "What is one case that should pass, and one that should fail?"
DECIDE = "What will you decide with the result?"
ASKED = ("decide", "tools", "agents", "evals")
DEFAULT_LEAD = re.compile(r"^default\b", re.I)


def items(text):
    visible = split_fences(text.lstrip("\ufeff"))[0]
    sections = parse(visible)[0]
    return {name: real_items(sections.get(name, [])) for name in ("Decided", "Open", "Parked")}


def literal(text):
    """The text with each `[insert ...]` outside code put in a code span. check_decisions has listed it, so the person
    said it is meant, and check_brief reads a code span as literal text."""
    return INSERT_FINDER.sub(lambda m: m.group("keep") or f"`{m.group()}`", text)


def literal_cases(item):
    """An Evals item with `stated: ` before each colon-labelled case body that holds a code span and that check_brief
    would fail as a placeholder, as in Pass: `N/A`. A case body that is only a placeholder with no code span is left
    as written, so check_brief fails it."""
    text, marks = case_marks(item)
    out, last = [], 0
    for i, (start, end, _, colon) in enumerate(marks):
        body = text[end:marks[i + 1][0] if i + 1 < len(marks) else len(text)]
        if colon and CODE_SPAN.search(body) and judge(body)[0] == "fail":
            lead = end + len(body) - len(body.lstrip())
            out += [text[last:lead], "stated: "]
            last = lead
    return "".join(out) + text[last:] if out else item


def written(text, slot, own=False):
    """A user value as written in brief slot `slot`, without its `stated:` labels. own is True for a slot's own value.

    One `stated:` goes in front when check_brief would read the value as a marker. See the module docstring.
    """
    raw = literal(unstated(text))
    if slot == "Evals":
        raw = literal_cases(raw)
    tag = TAG.match(raw)
    if ((tag and slot not in TAGS.get(tag.group(1).lower(), [])) or (DEFAULT_LEAD.match(raw) and not own)
            or UNKNOWN_START.match(raw) or is_bare_trap(raw) or classify(raw) == "fail"):
        return f"stated: {raw}"
    return raw


def slot_lines(rows, slot):
    return [row for row in rows if slot_of(row) == slot]


def question_of(row):
    """The question an Open or Parked line asks, with an ASCII `?`, which is the only mark check_brief reads."""
    extra = extra_of(row)
    text = (slot_value(row) if slot_of(row) else extra[1] if extra else row).strip()
    text = re.sub(r"^(?:\s*(?:unknown|stated)\s*:\s*)+", "", text, flags=re.I).lstrip("? ")
    if "?" in text:
        return text
    marks = [i for i, char in enumerate(text) if has_question(char)]
    return text[:marks[-1]] + "?" + text[marks[-1] + 1:] if marks else text.rstrip(".") + "?"


def unknown(text):
    return f"unknown: {literal(question_of(text))}"


def slot_text(decided, opens, slot, fallback):
    """Return (text, is_unknown)."""
    firm = slot_lines(decided, slot)
    if firm:
        return written(slot_value(firm[0]), BRIEF_SLOT[slot], own=True), False
    pending = slot_lines(opens, slot)
    return unknown(pending[0] if pending else fallback), True


def map_text(text, confirmed=()):
    """The brief for `text`. confirmed is the (slot, value) of each yes, copied into the `## Confirmed` block."""
    found = items(text)
    decided, opens, parked = found["Decided"], found["Open"], found["Parked"]
    lands = [landing(row) for row in decided]
    named = {label: value for _, value, label in lands if label in ASKED + ("write first",) and not blank(value)}
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
    ordered += [unknown(row) for row in parked if has_question(row)]
    lines = ["# Brief: from decisions", ""]
    lines.append(f"- Goal: {goal}")
    # Goal holds only the user's lines. The stock or Open decide question waits in Unknowns, so no line the mapper
    # adds sits beside the user's goal.
    lines += [f"  - {written(named['decide'], 'Goal')}"] if "decide" in named else []
    lines.append("- Done:")
    lines.append(f"  - {done}")
    lines += [f"  - {written(row, 'Done')}" for row in other]
    lines.append(f"- Output: {output}")
    lines.append("- Constraints:")
    lines.append(f"  - {limits}")
    lines.append(f"  - {REPORT}")
    lines += [f"  - {written(row, 'Constraints')}" for row in limits_out]
    for slot, name in (("Tools", "tools"), ("Agents and roles", "agents"), ("Evals", "evals")):
        lines += [f"- {slot}: {written(named[name], slot, own=True)}"] if name in named else [f"- {slot}:",
                                                                                               f"  - {question[name]}"]
        if name == "tools" and "write first" in named:
            lines.append(f"  - write first: {named['write first']}")
    lines.append("- Verification:")
    lines.append(f"  - {verify}")
    lines.append(f"  - {EVIDENCE}")
    if parked:
        lines.append("- Parking lot:")
        lines += [f"  - {written(row, 'Parking lot')}" for row in parked]
    if ordered:
        lines.append("- Unknowns:")
        lines += [f"  - {item}" for item in ordered]
        lines += ["", "## Questions", ""]
        lines += [f"{number}. {question_of(item)}" for number, item in enumerate(ordered[:3], 1)]
    if confirmed:
        lines += ["", "## Confirmed", ""] + [f"- {slot}: {value}" for slot, value in confirmed]
    return "\n".join(lines) + "\n"


def main(path, confirmed=None):
    text, answers_text, code = inputs(path, confirmed)
    if code:
        return code
    code, lines, result = report(text, path, answers_text)
    if code:
        print("\n".join(lines))
        return code
    print(map_text(text, result.used), end="")
    return 0


if __name__ == "__main__":
    utf8_output()
    if sys.argv[1:] in (["-h"], ["--help"]):
        print(__doc__.strip())
        sys.exit(0)
    args = arguments(sys.argv[1:], "usage: python3 check/map_decisions.py <decisions.md> [--confirmed <confirmed.md>]")
    sys.exit(3 if args is None else main(*args))
