"""Run: python3 check/test_check_brief.py"""
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from check_brief import check, find_workstreams  # noqa: E402

FAILS = []
RAN = []

GOOD = """# Brief: t

- Workstream: demo
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
WS_FILE = "a briefs/WORKSTREAMS file exists"
WS_LISTED = "Workstream is in the nearest WORKSTREAMS"
WS_FOLDER = "Workstream matches the parent folder"

expect("good brief passes", GOOD, set())
expect("Workstream is required", swap("- Workstream: demo\n", ""), {PRESENT})
expect("no path skips workstream path checks", swap("- Workstream: demo", "- Workstream: not-a-real-workstream"), set())
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
expect("code span after prose in Verify line fails",
       swap("  - m1: `python3 check_listings.py`", "  - m1: The status is `example`."), {HAS_CMD})
expect("leading spaces before the command pass",
       swap("  - m1: `python3 check_listings.py`", "  - m1:  `python3 check_listings.py`"), set())
expect("empty span at the start of a Verify line fails",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `` then a note"), {HAS_CMD})
expect("whitespace-only span then a note fails",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `   ` then a note"), {HAS_CMD})
expect("command first with a later code span in the note passes",
       swap("  - m1: `python3 check_listings.py`", "  - m1: `python3 check_listings.py` see `listings.csv`"), set())


def expect_fast(name, text, want, limit=1.0):
    RAN.append(name)
    start = time.perf_counter()
    results = check(text)
    elapsed = time.perf_counter() - start
    got = {check_name for check_name, fails in results if fails}
    reasons = []
    if got != want:
        reasons.append(f"wanted {sorted(want)}, got {sorted(got)}")
    if elapsed >= limit:
        reasons.append(f"took {elapsed:.3f}s, limit {limit:.1f}s")
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


expect_fast("unclosed backtick in Verify line does not backtrack",
            swap("  - m1: `python3 check_listings.py`", "  - m1: `" + "a" * 100000), {HAS_CMD})
expect_fast("long whitespace backticks in Verify line do not backtrack",
            swap("  - m1: `python3 check_listings.py`", "  - m1: `" + " " * 100000 + "`"), {HAS_CMD})

FIXTURES = os.path.join(HERE, "fixtures")
CHECK = os.path.join(HERE, "check_brief.py")


def expect_fixture(filename, want_fail, not_fail=(), want_pattern=None, want_skip=(), name=None):
    name = name or f"fixture {filename}"
    RAN.append(name)
    path = os.path.join(FIXTURES, filename)
    if not os.path.exists(path):
        path = os.path.join(HERE, filename)
    proc = subprocess.run([sys.executable, CHECK, path],
                          capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    if want_fail is None:
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
        return
    line = f"FAIL {want_fail}"
    if proc.returncode != 1 or line not in lines:
        FAILS.append(f"{name}: wanted exit 1 with {line!r}, got exit {proc.returncode}")
        return
    reasons = []
    for bad in not_fail:
        if f"FAIL {bad}" in lines:
            reasons.append(f"did not want FAIL {bad!r}")
    for skip in want_skip:
        if f"SKIP {skip}" not in lines:
            reasons.append(f"wanted SKIP {skip!r}")
        if f"PASS {skip}" in lines:
            reasons.append(f"did not want PASS {skip!r}")
    if want_pattern and not re.search(want_pattern, proc.stdout, re.I):
        reasons.append(f"wanted /{want_pattern}/ in output")
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


expect_fixture("briefs/demo/valid.md", None)
expect_fixture("briefs/demo/missing-id.md", HAS_ID)
expect_fixture("briefs/demo/missing-verify.md", HAS_VERIFY)
expect_fixture("briefs/demo/prose-only.md", HAS_CMD)
expect_fixture("briefs/demo/unknown-id.md", KNOWN_ID)
expect_fixture("briefs/demo/duplicate-id.md", UNIQUE_ID)
expect_fixture("briefs/demo/no-workstream.md", PRESENT)
# Separate tree with demo-only WORKSTREAMS: unknown-list/briefs/ghost/unknown-workstream.md
expect_fixture("unknown-list/briefs/ghost/unknown-workstream.md", WS_LISTED, not_fail=(WS_FOLDER,))
expect_fixture("briefs/demo/folder-mismatch.md", WS_FOLDER, not_fail=(WS_LISTED,))
expect_fixture("no-list/briefs/demo/brief.md", WS_FILE, not_fail=(WS_LISTED, WS_FOLDER),
               want_pattern=r"create.*WORKSTREAMS")
expect_fixture("briefs/demo/no-verify-command.md", HAS_CMD)
expect_fixture("briefs/demo/no-workstream.md", PRESENT,
               want_pattern=r"add `?- Workstream: demo`?",
               name="no-workstream fixture suggests folder workstream")
expect_fixture("briefs/demo/no-workstream.md", PRESENT,
               want_skip=(WS_FILE, WS_LISTED, WS_FOLDER),
               name="no-workstream fixture skips workstream path checks")
expect_fixture("no-list/briefs/demo/brief.md", WS_FILE,
               not_fail=(WS_LISTED, WS_FOLDER),
               want_pattern=r"create.*WORKSTREAMS",
               want_skip=(WS_LISTED, WS_FOLDER),
               name="no-list fixture skips downstream workstream checks")


def expect_find_workstreams_from_subfolder():
    name = "find_workstreams from subfolder finds root list"
    RAN.append(name)
    with tempfile.TemporaryDirectory() as root:
        briefs_dir = os.path.join(root, "briefs")
        app_dir = os.path.join(root, "app")
        os.makedirs(briefs_dir)
        os.makedirs(app_dir)
        ws_file = os.path.join(briefs_dir, "WORKSTREAMS")
        with open(ws_file, "w") as f:
            f.write("demo\n")
        dummy = os.path.join(app_dir, "brief.md")
        with open(dummy, "w") as f:
            f.write("")
        got = find_workstreams(dummy)
        want = os.path.abspath(ws_file)
        if got != want:
            FAILS.append(f"{name}: wanted {want!r}, got {got!r}")


expect_find_workstreams_from_subfolder()


def expect_workstreams_list(name, ws_text, bad_line=None):
    RAN.append(name)
    with tempfile.TemporaryDirectory() as root:
        demo_dir = os.path.join(root, "briefs", "demo")
        os.makedirs(demo_dir)
        with open(os.path.join(root, "briefs", "WORKSTREAMS"), "w") as f:
            f.write(ws_text)
        brief_path = os.path.join(demo_dir, "brief.md")
        with open(brief_path, "w") as f:
            f.write(GOOD)
        proc = subprocess.run([sys.executable, CHECK, brief_path],
                              capture_output=True, text=True)
    if bad_line is None:
        if proc.returncode != 0:
            FAILS.append(f"{name}: wanted exit 0, got {proc.returncode}")
        return
    reasons = []
    if proc.returncode != 1:
        reasons.append(f"wanted exit 1, got {proc.returncode}")
    if not any(q in proc.stdout for q in (repr(bad_line), f'"{bad_line}"', f"`{bad_line}`")):
        reasons.append(f"wanted output to name {bad_line!r}")
    if not re.search(r"remove\b.*(?:spaces?|whitespace)", proc.stdout, re.I):
        reasons.append("wanted output to say to remove the spaces")
    if reasons:
        FAILS.append(f"{name}: {'; '.join(reasons)}")


expect_workstreams_list("WORKSTREAMS blank line with exact name passes", "\ndemo\n\n")
expect_workstreams_list("WORKSTREAMS padded name fails", " demo \n", bad_line=" demo ")
expect_workstreams_list("WORKSTREAMS trailing space fails", "demo \n", bad_line="demo ")
expect_workstreams_list("WORKSTREAMS tab fails", "\tdemo\n", bad_line="\tdemo")

if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
