"""Run: python3 check/test_check_brief.py"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
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
  - [m1] 3 bed. Proof is the listing.
- Taste: Modern, flag don't filter. Signal is the kitchen photo.
- Output: 10 rows with link and price.
- Verify:
  - m1: `python3 check_listings.py`
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
HAS_ID = "every Must-have has an id"
HAS_VERIFY = "every Must-have id has a Verify line"
HAS_CMD = "every Verify line has a backticked command"
KNOWN_ID = "every Verify line names a Must-have id"
UNIQUE_ID = "no id used twice"

expect("good brief passes", GOOD, set())
expect("missing slot", swap("- Output: 10 rows with link and price.\n", ""), {PRESENT})
expect("repeated slot", swap("- Skills: none.\n", "- Skills: none.\n- Skills: review-prd.\n"), {REPEAT})
expect("empty slot", swap("- Skills: none.", "- Skills:"), {EMPTY})
expect("Plan first is required", swap("- Plan first: none needed\n", ""), {PRESENT})
expect("Plan first yes with a plan", swap("- Plan first: none needed", "- Plan first: yes: show the sources first."), set())
expect("Plan first unknown fails", swap("- Plan first: none needed", "- Plan first: unknown: Want a plan?"), {PLAN})
expect("Kind is optional", swap("- Kind: search/decide\n", ""), set())
expect("label with a bracketed note", swap("- Taste: Modern", "- Taste (flag, don't filter): Modern"), set())
expect("label with a bracketed note is still one slot", swap("- Skills: none.", "- Skills: none.\n- Skills (later): review-prd."), {REPEAT})
expect("investigate and out of scope in Must-haves",
       swap("  - [m1] 3 bed. Proof is the listing.",
            "  - [m1] 3 bed. Proof is the listing.\n  - investigate: Does the listing say laundry?\n  - out of scope: houses."), set())
expect("out of scope in Taste fails", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste:\n  - Modern, flag don't filter. Signal is the kitchen photo.\n  - out of scope: reviews."), {TAGS})
expect("how in Skills", swap("- Skills: none.", "- Skills:\n  - none.\n  - how: in parallel, one agent per source."), set())
expect("how in Output fails", swap("- Output: 10 rows with link and price.", "- Output:\n  - 10 rows with link and price.\n  - how: in parallel."), {TAGS})
expect("default beside an unknown", swap("- Output: 10 rows with link and price.", "- Output: unknown: Which fields? Default offered: link and price."), {DEFAULT})
expect("default word in a slot with no unknown is fine", swap("- Output: 10 rows with link and price.", "- Output: 10 rows; the default sort is price."), set())
expect("label case does not matter", swap("- Parking lot:", "- parking lot:"), set())
expect("bare unknown", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown"), {UNK})
expect("unknown with no question mark", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown: tour or apply"), {UNK})
expect("unknown with a note after the question", swap("- Decision: unknown: Tour or apply?", "- Decision: unknown: Tour or apply? The speaker never said."), set())
expect("unknown in a sentence is prose, not a marker",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed. A rule answers yes, no or unknown."), set())
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
expect("adjective in a sub-item", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste:\n  - Modern, flag don't filter. Signal is the kitchen photo.\n  - Correct."), {TRAP})
expect("adjective with a signal passes", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: modern kitchen in the photos"), set())

expect("missing id",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed. Proof is the listing.\n  - 2 bath. Proof is the listing."), {HAS_ID})
expect("Must-have id with no Verify line",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed. Proof is the listing.\n  - [m2] 2 bath. Proof is the listing."), {HAS_VERIFY})
expect("prose-only Verify line",
       swap("  - m1: `python3 check_listings.py`", "  - m1: Check the listings by hand."), {HAS_CMD})
expect("empty backticks in Verify line",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `   `"), {HAS_CMD})
expect("unknown id in Verify line",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 check_listings.py`\n  - m2: `python3 check_bath.py`"), {KNOWN_ID})
expect("Verify line with no id at all",
       swap("- Verify:\n  - m1: `python3 check_listings.py`", "- Verify: Every claim names its photo, or says guess."),
       {HAS_VERIFY, HAS_CMD, KNOWN_ID})
expect("duplicate id among Must-haves",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed. Proof is the listing.\n  - [m1] 2 bath. Proof is the listing."), {UNIQUE_ID})
expect("duplicate id among Verify lines",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 check_listings.py`\n  - m1: `python3 check_other.py`"), {UNIQUE_ID})
expect("investigate, out of scope, and unknown need no id or Verify line",
       swap("  - [m1] 3 bed. Proof is the listing.",
            "  - [m1] 3 bed. Proof is the listing.\n  - investigate: Does it allow pets?\n  - out of scope: houses.\n  - unknown: Need parking?"), set())
expect("two rules with two Verify lines pass",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed. Proof is the listing.\n  - [m2] 2 bath. Proof is the listing.",
            swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 check_listings.py`\n  - m2: `python3 check_bath.py`")), set())
expect("Verify none with only investigate items passes",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - investigate: Does it allow pets?",
            swap("- Verify:\n  - m1: `python3 check_listings.py`", "- Verify: none")), set())
expect("Verify none with a rule fails",
       swap("- Verify:\n  - m1: `python3 check_listings.py`", "- Verify: none"), {HAS_VERIFY})
expect("note after Verify command passes",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 check_listings.py` exits 0 when all rows match"), set())
expect("Verify command may contain colon-space and command substitution",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 -c \"print('a: b')\" && echo $(date)`"), set())
expect("id with underscore and hyphen passes",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [bed_3-ok] 3 bed. Proof is the listing.",
            swap("  - m1: `python3 check_listings.py`", "  - bed_3-ok: `python3 check_listings.py`")), set())
expect("hedged rule with Verify passes",
       swap("  - [m1] 3 bed. Proof is the listing.", "  - [m1] 3 bed (hedged, confirm). Proof is the listing."), set())

FIXTURES = os.path.join(HERE, "fixtures")
CHECK = os.path.join(HERE, "check_brief.py")


def expect_fixture(filename, want_fail):
    name = f"fixture {filename}"
    RAN.append(name)
    proc = subprocess.run([sys.executable, CHECK, os.path.join(FIXTURES, filename)],
                          capture_output=True, text=True)
    if want_fail is None:
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
    else:
        line = f"FAIL {want_fail}"
        if proc.returncode != 1 or line not in proc.stdout.splitlines():
            FAILS.append(f"{name}: wanted exit 1 with {line!r}, got exit {proc.returncode}")


expect_fixture("valid.md", None)
expect_fixture("missing-id.md", HAS_ID)
expect_fixture("missing-verify.md", HAS_VERIFY)
expect_fixture("prose-only.md", HAS_CMD)
expect_fixture("unknown-id.md", KNOWN_ID)
expect_fixture("duplicate-id.md", UNIQUE_ID)

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
