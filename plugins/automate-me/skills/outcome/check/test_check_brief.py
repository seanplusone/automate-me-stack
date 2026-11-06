"""Run: python3 check/test_check_brief.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import check  # noqa: E402

FAILS = []
RAN = []

GOOD = """# Brief: t

- Kind: search/decide
- Plan first: none needed
- Goal: Find 10 listings.
- Decision: unknown: Tour or apply?
- Context: The couple pays 2600.
- Must-haves:
  - 3 bed. Proof is the listing.
- Taste: Modern, flag don't filter. Signal is the kitchen photo.
- Output: 10 rows with link and price.
- Verify: Every claim names its photo, or says guess.
- If stuck: Stop after one peek.
- Skills: none.
- Parking lot: none.
- Unknowns:
  - unknown: Tour or apply?

## Questions

1. Tour or apply?
"""


def failed(text):
    return {name for name, fails in check(text) if fails}


def expect(name, text, want):
    RAN.append(name)
    got = failed(text)
    if got != want:
        FAILS.append(f"{name}: wanted {sorted(want)}, got {sorted(got)}")


def swap(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new)


PRESENT, REPEAT, EMPTY = "every required slot present", "no slot repeated", "no empty slot"
PLAN, TAGS, DEFAULT = "Plan first says yes or none needed", "tagged items in their slots", "no default beside an unknown"
UNK, LIST, QS, TRAP = ("every unknown has a question", "Unknowns list matches the slots",
                       "at most 3 questions, each a question", "no bare trap adjective")

expect("good brief passes", GOOD, set())
expect("missing slot", swap("- Verify: Every claim names its photo, or says guess.\n", ""), {PRESENT})
expect("repeated slot", swap("- Skills: none.\n", "- Skills: none.\n- Skills: review-prd.\n"), {REPEAT})
expect("empty slot", swap("- Skills: none.", "- Skills:"), {EMPTY})
expect("Plan first is required", swap("- Plan first: none needed\n", ""), {PRESENT})
expect("Plan first yes with a plan", swap("- Plan first: none needed", "- Plan first: yes: show the sources first."), set())
expect("Plan first unknown fails", swap("- Plan first: none needed", "- Plan first: unknown: Want a plan?"), {PLAN})
expect("Kind is optional", swap("- Kind: search/decide\n", ""), set())
expect("label with a bracketed note", swap("- Taste: Modern", "- Taste (flag, don't filter): Modern"), set())
expect("label with a bracketed note is still one slot", swap("- Skills: none.", "- Skills: none.\n- Skills (later): review-prd."), {REPEAT})
expect("investigate and out of scope in Must-haves",
       swap("  - 3 bed. Proof is the listing.", "  - 3 bed. Proof is the listing.\n  - investigate: Does the listing say laundry?\n  - out of scope: houses."), set())
expect("out of scope in Taste fails", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste:\n  - Modern, flag don't filter. Signal is the kitchen photo.\n  - out of scope: reviews."), {TAGS})
expect("how in Skills", swap("- Skills: none.", "- Skills:\n  - none.\n  - how: in parallel, one agent per source."), set())
expect("how in Verify fails", swap("- Verify: Every claim names its photo, or says guess.", "- Verify:\n  - Every claim names its photo, or says guess.\n  - how: in parallel."), {TAGS})
expect("default beside an unknown", swap("- Output: 10 rows with link and price.", "- Output: unknown: Which fields? Default offered: link and price."), {DEFAULT})
expect("default word in a slot with no unknown is fine", swap("- Output: 10 rows with link and price.", "- Output: 10 rows; the default sort is price."), set())
expect("label case does not matter", swap("- Parking lot:", "- parking lot:"), set())
expect("bare unknown", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown"), {UNK})
expect("unknown with no question mark", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown: tour or apply"), {UNK})
expect("unknown with a note after the question", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown: Tour or apply? The speaker never said."), set())
expect("unknown in a sentence is prose, not a marker",
       swap("  - 3 bed. Proof is the listing.", "  - 3 bed. A rule answers yes, no or unknown."), set())
expect("Unknowns none while a slot is unknown", swap("- Unknowns:\n  - unknown: Tour or apply?", "- Unknowns: none"), {LIST})
expect("Unknowns holds a non-marker", swap("  - unknown: Tour or apply?\n\n", "  - unknown: Tour or apply?\n  - move-in date\n\n"), {LIST})
expect("unknowns but no questions", swap("## Questions\n\n1. Tour or apply?\n", ""), {QS})
expect("four questions", GOOD + "2. A?\n3. B?\n4. C?\n", {QS})
expect("three questions", GOOD + "2. A?\n3. B?\n", set())
expect("question with no mark", GOOD + "2. Tell me the date.\n", {QS})
expect("no unknowns, no questions", swap("- Decision: unknown: Tour or apply?", "- Decision: Which to tour.",
                                         swap("- Unknowns:\n  - unknown: Tour or apply?", "- Unknowns: none",
                                              swap("## Questions\n\n1. Tour or apply?\n", ""))), set())
expect("bare adjective", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: modern"), {TRAP})
expect("two bare adjectives with filler", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: it should be clean and modern"), {TRAP})
expect("adjective in a sub-item", swap("  - 3 bed. Proof is the listing.", "  - 3 bed. Proof is the listing.\n  - Correct."), {TRAP})
expect("adjective with a signal passes", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: modern kitchen in the photos"), set())

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
