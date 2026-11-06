"""Run: python3 check/test_score_case.py"""
import contextlib
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_case import score  # noqa: E402

FAILS = []
RAN = []

BRIEF = """# Brief: t

- Goal: Find 10 listings in Irvine.
- Decision: unknown: Tour or apply?
- Context: The couple pays 2600 and the tenant 1700. Up to 5k if it is really good.
- Must-haves: 3 bed. Proof is the listing.
- Taste: Modern, flag don't filter. Signal is the photos.
- Output: 10 rows.
- Verify: Check the photos, not the descriptions.
- If stuck: Peek the next 100 dollars up.
- Skills: none.
- Parking lot: A Facebook group.
- Unknowns:
  - unknown: Tour or apply?
  - unknown: Is 4300 the cap, or 5k?

## Questions

1. Tour or apply?
2. What move-in date do you need?
"""


def write(name, text):
    path = os.path.join(tempfile.mkdtemp(), name)
    open(path, "w").write(text)
    return path


def run(key, brief=BRIEF):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = score(write("key.md", key), write("brief.md", brief))
    return code, out.getvalue()


def expect(name, key, code, needle="", brief=BRIEF):
    RAN.append(name)
    got, out = run(key, brief)
    if got != code or needle not in out:
        FAILS.append(f"{name}: wanted exit {code} with {needle!r}, got exit {got}:\n{out}")


expect("fact verbatim", "Fact: 2600\nFact: Irvine\n", 0, "PASS 2/2")
expect("fact rounded fails", "Fact: 2600\n", 1, "not verbatim: 2600", brief=BRIEF.replace("2600", "2,600"))
expect("10 does not match 100", "Fact: 10\n", 1, "not verbatim", brief=BRIEF.replace("10 listings", "a few listings").replace("10 rows", "rows"))
expect("5k does not match 5,000 inside a number", "Fact: 5\n", 1, "not verbatim", brief=BRIEF.replace("5k", "5,000"))
expect("fact a/b alternation", "Fact: 5000/5k\n", 0, "PASS")
expect("fact $ term", "Fact: $100/100 dollars\n", 0, "PASS")
expect("slot terms all present", "Slot: Taste | modern | flag | photo\n", 0, "PASS")
expect("slot term missing", "Slot: Taste | modern | bedroom\n", 1, "does not name: bedroom")
expect("slot term found only in another slot fails", "Slot: Output | irvine\n", 1, "does not name: irvine")
expect("slot label case-insensitive", "Slot: if stuck | 100 dollars\n", 0, "PASS")
expect("unknown label fails cleanly", "Slot: Budget | 5k\n", 1, "MISSED")
expect("unknown found in a marker", "Unknown: cap | 4300 | 5k\n", 0, "PASS")
expect("unknown found in a question", "Unknown: move-in | move-in\n", 0, "PASS")
expect("unknown terms must share one item", "Unknown: mixed | tour | move-in\n", 1, "no unknown or question names")
expect("unknown stated as prose fails", "Unknown: area | commute\n", 1, "no unknown or question names: commute",
       brief=BRIEF.replace("- Skills: none.", "- Skills: none. The commute is short."))
expect("forbidden clear", "Forbidden: neighborhood | \\bwoodbridge\\b\n", 0, "clear")
expect("forbidden guessed", "Forbidden: cap | \\bcap\\b[^.?\\n]{0,25}4300\n", 1, "guessed a fact",
       brief=BRIEF.replace("- Output: 10 rows.", "- Output: 10 rows under the cap of 4300."))
expect("forbidden ignores questions", "Forbidden: cap | \\bcap\\b[^.?\\n]{0,25}4300\n", 0, "clear",
       brief=BRIEF.replace("Is 4300 the cap, or 5k?", "Is the cap 4300, or 5k?"))
expect("pet does not match carpet (old substring bug)", "Unknown: pets | pet\n", 1, "no unknown or question names: pet",
       brief=BRIEF.replace("Tour or apply?", "Is carpet in the bedrooms fine?"))
expect("pet matches pets", "Unknown: pets | pet\n", 0, "PASS",
       brief=BRIEF.replace("What move-in date do you need?", "Do you have pets?"))
expect("slot term 10 does not match 100", "Slot: If stuck | 10\n", 1, "does not name: 10")
expect("slot term matches a word start only", "Slot: Goal | sting\n", 1, "does not name: sting",
       brief=BRIEF.replace("Find 10 listings", "Find 10 existing listings"))
expect("phrase matches across spaces", "Slot: If stuck | next 100\n", 0, "PASS",
       brief=BRIEF.replace("next 100 dollars", "next  100 dollars"))
expect("any finds a term in any slot", "Any: tool | browser\n", 0, "PASS",
       brief=BRIEF.replace("- If stuck: Peek", "- If stuck: Check the browser works. Peek"))
expect("any misses a term nowhere in the brief", "Any: tool | browser\n", 1, "brief does not name: browser")
expect("a short term is a whole word", "Slot: Goal | ERD\n", 1, "does not name: ERD",
       brief=BRIEF.replace("Find 10 listings", "Draw an erDiagram of 10 listings"))
expect("a short term takes a plural s", "Slot: Goal | ERD\n", 0, "PASS",
       brief=BRIEF.replace("Find 10 listings", "Draw two ERDs of 10 listings"))
expect("pet is not petty", "Unknown: pets | pet\n", 1, "names: pet",
       brief=BRIEF.replace("Tour or apply?", "Is a petty fee fine?"))
expect("parking found", "Parking: fb | facebook\n", 0, "PASS")
expect("parking missing", "Parking: pricing | pricing page\n", 1, "parking lot does not name")
expect("key lines in a code block are ignored", "```\nFact: nowhere\n```\nFact: 2600\n", 0, "PASS 1/1")
expect("empty key fails", "# nothing\n", 1, "no scorable lines")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
