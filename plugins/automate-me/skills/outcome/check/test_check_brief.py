"""Run: python3 check/test_check_brief.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_brief import asks, check, classify, eval_cases, parse  # noqa: E402

FAILS = []
RAN = []

GOOD = """# Brief: t

- Kind: search/decide
- Plan first: none needed
- Goal:
  - Find 10 listings.
  - unknown: Tour or apply?
- Done:
  - 3 bed. Proof is the listing.
- Taste: Modern, flag don't filter. Signal is the kitchen photo.
- Output: 10 rows with link and price, as a list in the reply.
- Constraints: Stop after one peek. Report only.
- Tools: A browser that opens photos. Write first: none.
- Agents and roles: One agent searches. A second person checks the list.
- Evals:
  - Pass: a listing with 3 beds and a photo is kept.
  - Fail: a listing with no photo is dropped.
- Verification: Every claim names its photo, or says guess.
- Skills: none.
- Parking lot: none.
- Unknowns:
  - unknown: Tour or apply?

## Questions

1. Tour or apply?
"""

MIN = """# Brief: t

- Goal: Find 10 listings.
- Done: 3 bed. Proof is the listing.
- Output: 10 rows in the reply.
- Constraints: Stop after one peek.
- Tools: A browser. Write first: none.
- Agents and roles: One agent searches.
- Evals:
  - Pass: keep a 3 bed listing.
  - Fail: drop a listing with no photo.
- Verification: Every claim names its photo, or says guess.
"""


def failed(text):
    return {name for name, fails in check(text) if fails}


def expect(name, text, want):
    RAN.append(name)
    got = failed(text)
    if got != want:
        FAILS.append(f"{name}: wanted {sorted(want)}, got {sorted(got)}")


def outcome(text):
    """'fail', 'ask' or 'pass' for a whole brief, by the exit-code precedence."""
    return "fail" if failed(text) else "ask" if asks(text) else "pass"


def expect_outcome(name, text, want):
    RAN.append(name)
    got = outcome(text)
    if got != want:
        FAILS.append(f"{name}: wanted {want}, got {got}; failed {sorted(failed(text))}, asks {asks(text)}")


def swap(old, new, text=GOOD):
    assert old in text, old
    return text.replace(old, new)


PRESENT, REPEAT, EMPTY = "every required slot present", "no slot repeated", "no empty slot"
PLAN, TAGS, DEFAULT = "Plan first says yes or none needed", "tagged items in their slots", "no default beside an unknown"
UNK, LIST, QS, TRAP = ("every unknown has a question", "Unknowns list matches the slots",
                       "at most 3 questions, each a question", "no bare trap adjective")

expect("good brief passes", GOOD, set())
expect("required slots alone pass", MIN, set())
EVALS = """- Evals:
  - Pass: keep a 3 bed listing.
  - Fail: drop a listing with no photo.
"""
expect("missing Evals", MIN.replace(EVALS, ""), {PRESENT})
for label, line in (
    ("Goal", "- Goal: Find 10 listings.\n"),
    ("Done", "- Done: 3 bed. Proof is the listing.\n"),
    ("Output", "- Output: 10 rows in the reply.\n"),
    ("Constraints", "- Constraints: Stop after one peek.\n"),
    ("Tools", "- Tools: A browser. Write first: none.\n"),
    ("Agents and roles", "- Agents and roles: One agent searches.\n"),
    ("Evals", EVALS),
    ("Verification", "- Verification: Every claim names its photo, or says guess.\n"),
):
    expect(f"missing {label}", MIN.replace(line, ""), {PRESENT})

CASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cases", "missing-evals", "runs", "run-1", "brief.md"))
with open(CASE) as handle:
    case_text = handle.read()
expect("missing-evals case fails the shape check", case_text, {PRESENT})
RAN.append("missing-evals case names only Evals")
details = [f for _, fails in check(case_text) for f in fails]
if details != ["missing slot: Evals"]:
    FAILS.append(f"missing-evals case names only Evals: got {details}")

expect("repeated slot", swap("- Skills: none.\n", "- Skills: none.\n- Skills: review-prd.\n"), {REPEAT})
expect("empty slot", swap("- Skills: none.", "- Skills:"), {EMPTY})
expect("Plan first is optional", swap("- Plan first: none needed\n", ""), set())
expect("Plan first yes with a plan", swap("- Plan first: none needed", "- Plan first: yes: show the sources first."), set())
expect("Plan first unknown fails", swap("- Plan first: none needed", "- Plan first: unknown: Want a plan?"), {PLAN})
expect("Kind is optional", swap("- Kind: search/decide\n", ""), set())
expect("Taste is optional", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.\n", ""), set())
expect("Skills, Parking lot and Unknowns are optional",
       swap("- Skills: none.\n- Parking lot: none.\n- Unknowns:\n  - unknown: Tour or apply?\n", ""), set())
expect("label with a bracketed note", swap("- Taste: Modern", "- Taste (flag, don't filter): Modern"), set())
expect("label with a bracketed note is still one slot", swap("- Skills: none.", "- Skills: none.\n- Skills (later): review-prd."), {REPEAT})
expect("investigate in Done and out of scope in Constraints",
       swap("  - 3 bed. Proof is the listing.", "  - 3 bed. Proof is the listing.\n  - investigate: Does the listing say laundry?",
            swap("- Constraints: Stop after one peek. Report only.", "- Constraints:\n  - Stop after one peek. Report only.\n  - out of scope: houses.")), set())
expect("out of scope in Taste fails", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste:\n  - Modern, flag don't filter. Signal is the kitchen photo.\n  - out of scope: reviews."), {TAGS})
expect("how in Agents and roles", swap("- Agents and roles: One agent searches. A second person checks the list.",
                                        "- Agents and roles:\n  - One agent searches.\n  - how: in parallel, one agent per source."), set())
expect("how in Verification fails", swap("- Verification: Every claim names its photo, or says guess.", "- Verification:\n  - Every claim names its photo, or says guess.\n  - how: in parallel."), {TAGS})
expect("default beside an unknown", swap("- Output: 10 rows with link and price, as a list in the reply.",
                                        "- Output:\n  - unknown: Which fields?\n  - default: link and price."), {DEFAULT})
expect("default inside an unknown question passes", swap("- Output: 10 rows with link and price, as a list in the reply.",
                                                          "- Output: unknown: Should the default be price?"), set())
expect("default word in a slot with no unknown is fine", swap("- Output: 10 rows with link and price, as a list in the reply.", "- Output: 10 rows; the default sort is price."), set())
expect("label case does not matter", swap("- Parking lot:", "- parking lot:"), set())
expect("bare unknown", swap("- unknown: Tour or apply?", "- unknown"), {UNK})
expect("unknown with no question mark", swap("unknown: Tour or apply?", "unknown: tour or apply"), {UNK})
expect("unknown with a note after the question", swap("unknown: Tour or apply?", "unknown: Tour or apply? The speaker never said."), set())
expect("unknown in a sentence is prose, not a marker",
       swap("  - 3 bed. Proof is the listing.", "  - 3 bed. A rule answers yes, no or unknown."), set())
expect("Unknowns none while a slot is unknown", swap("- Unknowns:\n  - unknown: Tour or apply?", "- Unknowns: none"), {LIST})
expect("Unknowns holds a non-marker", swap("  - unknown: Tour or apply?\n\n", "  - unknown: Tour or apply?\n  - move-in date\n\n"), {LIST})
expect("unknowns but no questions", swap("## Questions\n\n1. Tour or apply?\n", ""), {QS})
expect("four questions", GOOD + "2. A?\n3. B?\n4. C?\n", {QS})
expect("three questions", GOOD + "2. A?\n3. B?\n", set())
expect("question with no mark", GOOD + "2. Tell me the date.\n", {QS})
expect("no unknowns, no questions",
       swap("- Goal:\n  - Find 10 listings.\n  - unknown: Tour or apply?", "- Goal: Find 10 listings.",
            swap("- Unknowns:\n  - unknown: Tour or apply?", "- Unknowns: none",
                 swap("## Questions\n\n1. Tour or apply?\n", ""))), set())
expect("bare adjective", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: modern"), {TRAP})
expect("two bare adjectives with filler", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: it should be clean and modern"), {TRAP})
expect("adjective in a sub-item", swap("  - 3 bed. Proof is the listing.", "  - 3 bed. Proof is the listing.\n  - Correct."), {TRAP})
expect("adjective with a signal passes", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: modern kitchen in the photos"), set())
expect("check is filler, so a bare correct fails", swap("- Taste: Modern, flag don't filter. Signal is the kitchen photo.", "- Taste: Check it is correct."), {TRAP})

PLACE = "no placeholder"
REQUIRED = ["Goal", "Done", "Output", "Constraints", "Tools", "Agents and roles", "Evals", "Verification"]
TBD = "# Brief: t\n" + "".join(f"- {s}: TBD\n" for s in REQUIRED)
RAN.append("every slot TBD names each required slot")
tbd_msgs = [f for _, fails in check(TBD) for f in fails]
if not all(any(s in msg and "placeholder" in msg for msg in tbd_msgs) for s in REQUIRED):
    FAILS.append(f"every slot TBD names each required slot: {tbd_msgs}")

for ph in ("TBD", "TODO", "N/A", "...", "-", "?", "(later)", "[later]", "none"):
    RAN.append(f"Evals placeholder {ph}")
    msgs = [f for _, fails in check(MIN.replace(EVALS, f"- Evals: {ph}\n")) for f in fails]
    if not any("Evals" in msg and "placeholder" in msg for msg in msgs):
        FAILS.append(f"Evals placeholder {ph}: {msgs}")

# Real Evals content with no fail case asks rather than fails (round 4).
expect_outcome("pass case only asks", MIN.replace(EVALS, "- Evals:\n  - Pass: keep a 3 bed listing.\n"), "ask")
expect("should pass and should fail", MIN.replace(EVALS, "- Evals: One row should pass, and one row should fail.\n"), set())
expect("numbered evals", MIN.replace(EVALS, "- Evals:\n  1. Pass: keep a listing.\n  2. Fail: drop a listing.\n"), set())
expect("evals inside a fence", MIN.replace(EVALS, "```\n- Evals:\n  - Pass: keep a listing.\n  - Fail: drop a listing.\n```\n"), {PRESENT})
expect("evals inside a tilde fence", MIN.replace(EVALS, "~~~\n- Evals:\n  - Pass: keep a listing.\n  - Fail: drop a listing.\n~~~\n"), {PRESENT})
expect("write first none with no tool is a placeholder",
       MIN.replace("- Tools: A browser. Write first: none.\n", "- Tools: write first: none\n"), {PLACE})
expect("one line pass and fail", MIN.replace(EVALS, "- Evals: Pass: keep a row. Fail: drop a row.\n"), set())
expect("bold pass and fail", MIN.replace(EVALS, "- Evals:\n  - **Pass:** keep a row.\n  - **Fail:** drop a row.\n"), set())
expect("must pass and must fail", MIN.replace(EVALS, "- Evals: One row must pass, and one row must fail.\n"), set())
expect("real text in parentheses", MIN.replace("- Output: 10 rows in the reply.\n", "- Output: (one PDF of 24 half-sheet cards).\n"), set())
expect("none with a reason on Tools",
       MIN.replace("- Tools: A browser. Write first: none.\n", "- Tools: none: the person already has the pages.\n"), set())
expect("none with a reason on Constraints",
       MIN.replace("- Constraints: Stop after one peek.\n", "- Constraints: none: this search has no hard stop.\n"), set())
expect("bare none on Constraints", MIN.replace("- Constraints: Stop after one peek.\n", "- Constraints: none.\n"), {PLACE})

for bad in ("- Evals:\n  - Pass: TBD\n  - Fail: drop a row.\n",
            "- Evals:\n  - Pass: keep a row.\n  - Fail: TBD\n",
            "- Evals:\n  - Pass:\n  - Fail: drop a row.\n",
            "- Evals:\n  - Pass: keep a row.\n  - Fail:\n"):
    RAN.append(f"bad eval {bad.splitlines()[-1]}")
    msgs = [m for _, fs in check(MIN.replace(EVALS, bad if bad.endswith("\n") else bad + "\n")) for m in fs]
    if not any("Evals" in m for m in msgs):
        FAILS.append(f"bad eval not named: {bad!r} -> {msgs}")

expect_outcome("Fail-safe is not a fail case, so it asks",
               MIN.replace(EVALS, "- Evals:\n  - Pass: keep a row.\n  - Fail-safe: the run stops.\n"), "ask")

for ph in ("**TBD**", "`TBD`", "TBD!", "TBD:", "N / A", "TBD later", "TBC", "<goal here>", "{{goal}}", "placeholder"):
    RAN.append(f"required placeholder {ph}")
    msgs = [m for _, fs in check(MIN.replace("- Goal: Find 10 listings.\n", f"- Goal: {ph}\n")) for m in fs]
    if not any("Goal" in m and "placeholder" in m for m in msgs):
        FAILS.append(f"required placeholder {ph}: {msgs}")

after = MIN.replace(
    "- Evals:\n  - Pass: keep a 3 bed listing.\n  - Fail: drop a listing with no photo.\n",
    "- Evals:\n````\nignored\n```\nstill inside\n````\n  - Pass: keep a listing.\n  - Fail: drop a listing.\n",
)
expect("item after a fence still counts", after, set())
stolen = MIN.replace(
    "- Goal: Find 10 listings.\n",
    "- Goal: Find 10 listings.\n````\n- Goal: stolen\n```\nstill inside\n````\n",
)
RAN.append("inner fence does not close a longer fence")
slots, _, counts, _ = parse(stolen)
if slots.get("Goal") != ["Find 10 listings."] or counts.get("Goal") != 1:
    FAILS.append(f"inner fence does not close a longer fence: {slots.get('Goal')} x{counts.get('Goal')}")

RAN.append("dotless i label fails without a traceback")
dotless = GOOD.replace("- Verification:", "- Ver\u0131fication:")
path = os.path.join(tempfile.mkdtemp(), "brief.md")
with open(path, "w") as handle:
    handle.write(dotless)
script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_brief.py")
ran = subprocess.run([sys.executable, script, path], capture_output=True, text=True)
if ran.returncode != 1 or "Traceback" in ran.stderr or "Traceback" in ran.stdout or "Verification" not in ran.stdout:
    FAILS.append(f"dotless i label fails without a traceback: exit {ran.returncode}\n{ran.stdout}\n{ran.stderr}")

def slot(label, block, text=MIN):
    """MIN with one slot (and its sub-items) replaced by block."""
    lines, out, skip = text.splitlines(), [], False
    for line in lines:
        if line.startswith(f"- {label}:"):
            out.append(block)
            skip = True
            continue
        if skip and line.startswith("  "):
            continue
        skip = False
        out.append(line)
    assert any(line.startswith(f"- {label}:") for line in lines), label
    return "\n".join(out) + "\n"


# Round 3, R3-A: placeholders that used to pass. All FAIL now.
for v in ("To be determined.", "To be decided.", "To be confirmed.", "Pending.", "TBA", "FIXME", "XXX", "TODO: fill in",
          "Fill in later.", "See below.", "See above.", "Same as above.", "<goal>.", "[insert goal]", "{goal}", "${goal}",
          "tbd/tbc", "<what the person decides, or unknown: <question>?>"):
    expect_outcome(f"R3-A Goal {v} fails", slot("Goal", f"- Goal: {v}"), "fail")
expect_outcome("R3-A write first: TBD fails", slot("Tools", "- Tools: write first: TBD"), "fail")
expect_outcome("R3-A none: to be determined fails", slot("Tools", "- Tools: none: to be determined"), "fail")
expect_outcome("R3-A unfilled Evals template fails",
               slot("Evals", "- Evals:\n  - Pass: <one case that meets Done>\n  - Fail: <one case that does not>"), "fail")
expect_outcome("R3-A Evals To be determined / Pending fails",
               slot("Evals", "- Evals:\n  - Pass: To be determined.\n  - Fail: Pending."), "fail")
expect_outcome("R3-A investigate: <question> fails", slot("Done", "- Done:\n  - 3 bed.\n  - investigate: <question>"), "fail")
# A hole inside a longer value asks rather than fails (round 4).
expect_outcome("a template hole beside real text asks", slot("Output", "- Output: 10 rows, sorted by <field>."), "ask")
expect_outcome("a hole in an optional slot fails", MIN + "- Parking lot: <tangents, not acted on>\n", "fail")
# Deliberately left out: a placeholder in another language is not on the list. The read-back catches it.
expect_outcome("R3-A Por determinar passes (not on the list, by design)", slot("Goal", "- Goal: Por determinar."), "pass")

SKILL_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "SKILL.md")
with open(SKILL_MD) as handle:
    template = handle.read().split("```\n# Brief: <short title>\n", 1)[1].split("```", 1)[0]
RAN.append("SKILL.md template pasted unfilled fails every required slot, the holes and Kind")
got = failed("# Brief: t\n" + template)
want = {PLACE, "no template hole", "Kind is one kind"}
if not want <= got:
    FAILS.append(f"SKILL.md template: wanted {sorted(want)} within {sorted(got)}")
msgs = [m for _, fs in check("# Brief: t\n" + template) for m in fs]
for s in REQUIRED:
    RAN.append(f"SKILL.md template names {s} as a placeholder")
    if f"slot {s} is only a placeholder" not in msgs:
        FAILS.append(f"SKILL.md template names {s} as a placeholder: {msgs}")
expect("Kind with a real kind", MIN + "- Kind: build\n", set())

# Round 3, R3-B and R3-C: real values. All PASS.
for v in ("上线第二版。", "Запустить вторую версию.", "Νέα έκδοση.", "新しい版を出す。", "Ship v2.", "Make v2.",
          "Make it faster.", "Check the logs.", "Lancer la version deux."):
    expect_outcome(f"real Goal {v} passes", slot("Goal", f"- Goal: {v}"), "pass")
for v in ("`make`", "git", "gRPC", "C#", ".env", "k8s"):
    expect_outcome(f"real Tools {v} passes", slot("Tools", f"- Tools: {v}"), "pass")
for label, block in (("Verification", "- Verification: `make check`"), ("Constraints", "- Constraints: Under $500."),
                     ("Constraints", "- Constraints: $500"), ("Done", "- Done: #123"), ("Output", "- Output: 24"),
                     ("Output", "- Output: 24 cards"), ("Constraints", "- Constraints: p95 < 200ms"),
                     ("Verification", "- Verification: `curl localhost/items/{id}` returns 200."),
                     ("Done", "- Done: proof is <https://example.com/listing/1>."),
                     ("Done", "- Done: a < b and c > d for every row.")):
    expect_outcome(f"real {label} {block[len(label) + 4:]} passes", slot(label, block), "pass")
expect_outcome("bare status codes are real cases", slot("Evals", "- Evals:\n  - Pass: 200\n  - Fail: 404"), "pass")
expect_outcome("a colon label and a phrase in one item",
               slot("Evals", "- Evals: Pass: a complete listing. A listing without a price should fail."), "pass")
expect_outcome("Evals unknown passes when Questions holds it, whatever its wording",
               slot("Evals", "- Evals:\n  - unknown: Which cases prove it works?") + "\n## Questions\n\n1. Which cases prove it works?\n",
               "pass")
expect("Evals unknown with no Questions block fails", slot("Evals", "- Evals:\n  - unknown: Which cases prove it works?"), {QS})
expect_outcome("a bare number is not an Evals case, so it asks", slot("Evals", "- Evals: 123"), "ask")

# Needs-human: suspicious but not on the list. exit 2, one ASK line each.
for label, block in (("Goal", "- Goal: maybe"), ("Goal", "- Goal: It depends."), ("Goal", "- Goal: We'll see."),
                     ("Goal", "- Goal: not sure"), ("Output", "- Output: ok"), ("Output", "- Output: x"),
                     ("Output", "- Output: →"), ("Done", "- Done: --> <--"), ("Goal", "- Goal: 版")):
    expect_outcome(f"needs-human {block}", slot(label, block), "ask")
expect_outcome("one-letter Evals cases ask", slot("Evals", "- Evals:\n  - Pass: x\n  - Fail: y"), "ask")
# A pronoun before 'should pass' is a single short token, so it asks rather than fails (round 2 had it FAIL).
expect_outcome("It should pass or should fail, TBD asks", slot("Evals", "- Evals: It should pass or should fail, TBD."), "ask")
expect_outcome("a hedge in an optional slot does not ask", MIN + "- Parking lot: maybe\n", "pass")
expect_outcome("FAIL wins over ASK", slot("Goal", "- Goal: TBD", slot("Output", "- Output: ok")), "fail")

RAN.append("classify API")
for value, want in (("TBD", "fail"), ("", "fail"), ("<goal>", "fail"), ("maybe", "ask"), ("ok", "ask"),
                    ("24", "pass"), ("$500", "pass"), ("`make`", "pass"), ("Por determinar", "pass")):
    if classify(value) != want:
        FAILS.append(f"classify({value!r}) = {classify(value)!r}, wanted {want!r}")

confirmed = slot("Output", "- Output: ok") + "\n## Confirmed\n\n- Output: ok\n"
expect_outcome("a recorded confirmation turns ASK into PASS", confirmed, "pass")
expect("the Confirmed block does not repeat the slot", confirmed, set())
expect_outcome("a confirmation of another value still asks",
               slot("Output", "- Output: ok") + "\n## Confirmed\n\n- Output: fine\n", "ask")
# Under any other heading the line is a second Output slot, so it fails as a repeat instead of confirming.
expect_outcome("only a heading named Confirmed confirms",
               slot("Output", "- Output: ok") + "\n## Confirmed assumptions\n\n- Output: ok\n", "fail")
expect_outcome("extra spaces inside a listed phrase still fail", slot("Goal", "- Goal: to  be determined"), "fail")
expect_outcome("a code span in an Evals case is not a hole",
               slot("Evals", "- Evals: Pass: `<input>` is read. Fail: missing input."), "pass")
expect_outcome("a confirmation does not lift a FAIL", slot("Goal", "- Goal: TBD") + "\n## Confirmed\n\n- Goal: TBD\n", "fail")
expect_outcome("a confirmed Evals case passes",
               slot("Evals", "- Evals:\n  - Pass: x\n  - Fail: y") + "\n## Confirmed\n\n- Evals: x\n- Evals: y\n", "pass")


# Round 4: every line of round4/repro/run.sh, with its target outcome.
GOOD_MD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cases", "apartment-search", "runs", "run-1", "brief.md")
with open(GOOD_MD) as handle:
    APT = handle.read()
expect_outcome("R4 base apartment brief passes", APT, "pass")
# X1: one on-list placeholder among real items fails, per item.
for label, block in (("Done", "- Done:\n  - Ten listings with a link each.\n  - TBD"),
                     ("Verification", "- Verification:\n  - Every claim names its listing link.\n  - N/A"),
                     ("Evals", "- Evals:\n  - Pass: TBD\n  - Pass: one listing has a photo.\n  - Fail: one listing has no photo.")):
    expect_outcome(f"R4 X1 {label} with one TBD item fails", slot(label, block, APT), "fail")
# X2: on-list variants fail once core() normalizes them; a placeholder with only a hedge beside it fails.
for v in ("N.A.", "n.a.", "to-be-determined", "TO_BE_DETERMINED", "fill-in", "To be *determined*.", "maybe tbd",
          "T.B.D.", "later, maybe", "ＴＢＤ", "“write first: TBD”"):
    expect_outcome(f"R4 X2 Output {v} fails", slot("Output", f"- Output: {v}", APT), "fail")
# X3: hedge-only values ask.
for v in ("We will *see*.", "not sure yet", "unclear", "maybe, maybe not", "write first: depends", "idk tbh", "depending"):
    expect_outcome(f"R4 X3 Output {v} asks", slot("Output", f"- Output: {v}", APT), "ask")
# X4: real values with a hole-like part ask or pass, never fail.
for v in ("Rows as JSON {link, price}, one per listing.", "A Vec<String> of listing links.", "Write under ${HOME}/out.",
          "p95<target and p99>budget", "Call <tel:+15551234567> for help.", "Press <Enter> to submit.",
          "Mail <user@example.com> the list.", "A `` `<col>` `` span and nothing else."):
    RAN.append(f"R4 X4 Output {v} never fails")
    if outcome(slot("Output", f"- Output: {v}", APT)) == "fail":
        FAILS.append(f"R4 X4 Output {v} never fails: {[f for _, fs in check(slot('Output', f'- Output: {v}', APT)) for f in fs]}")
expect_outcome("R4 X4 autolink passes", slot("Output", "- Output: Call <tel:+15551234567> for help.", APT), "pass")
# X5: whole-value holes still fail; a hole inside a file name asks.
for v in ("<goal>.", "[insert goal]", "{goal}", "< output >", "{{ }}", "Ten rows. [insert the cap]",
          "<what comes back, how many, which fields, and how the person sees it>"):
    expect_outcome(f"R4 X5 Output {v} fails", slot("Output", f"- Output: {v}", APT), "fail")
expect_outcome("R4 X5 One file named <name>.csv. asks", slot("Output", "- Output: One file named <name>.csv.", APT), "ask")
expect_outcome("R4 a SKILL.md template line fails", slot("Plan first", "- Plan first: yes: <what the plan shows first> | none needed", APT), "fail")
# X6: Evals.
expect_outcome("R4 X6 a code literal pass: is not a label",
               slot("Evals", "- Evals:\n  - A log containing `pass:` should pass.\n  - A missing log should fail.", APT), "pass")
RAN.append("R4 X6 Pass case: labels pass or ask")
if outcome(slot("Evals", "- Evals:\n  - Pass case: one listing has a photo.\n  - Fail case: one listing has no photo.", APT)) == "fail":
    FAILS.append("R4 X6 Pass case: labels pass or ask: got fail")
expect_outcome("R4 X6 a Fail item that says should pass has no pass case",
               slot("Evals", "- Evals:\n  - Fail: a listing that should pass the price rule but has no photo is dropped.", APT), "ask")
expect_outcome("R4 X6 Pass: ok; Fail: depends asks", slot("Evals", "- Evals:\n  - Pass: ok; Fail: depends", APT), "ask")
RAN.append("R4 X6 one ASK per case body")
if asks(slot("Evals", "- Evals:\n  - Pass: ok; Fail: depends", APT)) != [("Evals", "ok"), ("Evals", "depends")]:
    FAILS.append(f"R4 X6 one ASK per case body: {asks(slot('Evals', '- Evals:\n  - Pass: ok; Fail: depends', APT))}")
whole = slot("Evals", "- Evals:\n  - Pass: ok; Fail: depends", APT) + "\n## Confirmed\n\n- Evals: Pass: ok; Fail: depends\n"
expect_outcome("R4 S6 a whole-line confirmation does not lift the case bodies", whole, "ask")
# X7: other checks.
expect_outcome("R4 X7 Unknown at the start of plain text passes", slot("Output", "- Output: Unknown column names listed in a CSV.", APT), "pass")
expect_outcome("R4 X7 a digit is a visible signal", slot("Output", "- Output: 24 is valid", APT), "pass")
expect_outcome("R4 X7 Taste: TBD fails", slot("Taste", "- Taste: TBD", APT), "fail")
expect("R4 unknown alone is still a marker", swap("- unknown: Tour or apply?", "- unknown"), {UNK})
# Nits.
expect_outcome("R4 only the exact ## Confirmed heading confirms", slot("Output", "- Output: ok") + "\n# Confirmed\n\n- Output: ok\n", "fail")
RAN.append("R4 ASK shows the value as written")
if asks(slot("Output", "- Output: ->")) != [("Output", "->")] or asks(slot("Output", "- Output: ‘maybe’")) != [("Output", "‘maybe’")]:
    FAILS.append(f"R4 ASK shows the value as written: {asks(slot('Output', '- Output: ->'))}")
for v in ("?", "???", "-", "—", "..."):
    expect_outcome(f"R4 punctuation only {v} fails", slot("Output", f"- Output: {v}"), "fail")
for v in ("→", "\U0001F680"):
    expect_outcome(f"R4 symbols only {v} asks", slot("Output", f"- Output: {v}"), "ask")
RAN.append("R4 classify API")
for value, want in (("N.A.", "fail"), ("maybe tbd", "fail"), ("not sure yet", "ask"), ("${goal}", "fail"),
                    ("Vec<String>", "ask"), ("`Vec<String>`", "pass"), ("p95 < 200ms", "pass")):
    if classify(value) != want:
        FAILS.append(f"classify({value!r}) = {classify(value)!r}, wanted {want!r}")

# Round 4 fix review (codex): each repro, with its target outcome.
expect_outcome("R4 review Not pending. asks, not fails", slot("Done", "- Done: Not pending."), "ask")
expect_outcome("R4 review a regex quantifier {2,4} passes", slot("Done", "- Done: {2,4}"), "pass")
expect_outcome("R4 review [insert] before the first Evals label fails",
               slot("Evals", "- Evals: [insert evals] Pass: keep a row. Fail: drop a row."), "fail")
expect_outcome("R4 review a Fail item with an inline should pass; asks",
               slot("Evals", "- Evals: Fail: drop a broken row. Valid rows should pass; record the count."), "ask")
expect_outcome("R4 review real text before the first Evals label passes",
               slot("Evals", "- Evals: Happy path. Pass: keep a row. Fail: drop a row."), "pass")
RAN.append("R4 review ASK keeps a trailing comma on a whole item")
if asks(slot("Done", "- Done: We’ll see,")) != [("Done", "We’ll see,")]:
    FAILS.append(f"R4 review ASK keeps a trailing comma: {asks(slot('Done', '- Done: We’ll see,'))}")


def run_cli(text):
    path = os.path.join(tempfile.mkdtemp(), "brief.md")
    with open(path, "w") as handle:
        handle.write(text)
    return subprocess.run([sys.executable, script, path], capture_output=True, text=True)


for name, text, code, last in (("PASS exits 0", MIN, 0, "PASS brief:"),
                               ("FAIL exits 1", slot("Goal", "- Goal: TBD"), 1, "FAIL brief:"),
                               ("ASK exits 2", slot("Output", "- Output: ok"), 2, "ASK brief:"),
                               ("FAIL and ASK exits 1", slot("Goal", "- Goal: TBD", slot("Output", "- Output: ok")), 1, "FAIL brief:"),
                               ("confirmed ASK exits 0", confirmed, 0, "PASS brief:")):
    RAN.append(f"cli {name}")
    ran = run_cli(text)
    if ran.returncode != code or not ran.stdout.strip().splitlines()[-1].startswith(last):
        FAILS.append(f"cli {name}: exit {ran.returncode}\n{ran.stdout}")
RAN.append("cli ASK line format")
ran = run_cli(slot("Output", "- Output: ok", slot("Evals", "- Evals:\n  - Pass: x\n  - Fail: drop a row.")))
ask_lines = [line for line in ran.stdout.splitlines() if line.startswith("ASK:")]
if ask_lines != ["ASK: Output: Is 'ok' a real answer for Output?", "ASK: Evals: Is 'x' a real answer for Evals?"]:
    FAILS.append(f"cli ASK line format: {ask_lines}\n{ran.stdout}")
RAN.append("cli FAIL lines and ASK lines are distinct")
ran = run_cli(slot("Goal", "- Goal: TBD", slot("Output", "- Output: ok")))
if "FAIL no placeholder" not in ran.stdout or "ASK: Output:" not in ran.stdout:
    FAILS.append(f"cli FAIL lines and ASK lines are distinct:\n{ran.stdout}")


for name, args, data in (("missing file", ["/no/such/brief.md"], None), ("directory", [tempfile.mkdtemp()], None),
                         ("non-UTF-8 file", None, b"- Goal: \xff\xfe\n")):
    RAN.append(f"cli usage error: {name} exits 3 with one line")
    if data is not None:
        args = [os.path.join(tempfile.mkdtemp(), "brief.md")]
        with open(args[0], "wb") as handle:
            handle.write(data)
    ran = subprocess.run([sys.executable, script, *args], capture_output=True, text=True)
    lines = (ran.stdout + ran.stderr).strip().splitlines()
    if ran.returncode != 3 or len(lines) != 1 or "Traceback" in ran.stderr:
        FAILS.append(f"cli usage error {name}: exit {ran.returncode}\n{ran.stdout}{ran.stderr}")
RAN.append("cli hole ASK line format")
ran = run_cli(slot("Output", "- Output: Press <Enter> to submit."))
if "ASK: Output: Is 'Press <Enter> to submit.' a real answer for Output, or a hole to fill?" not in ran.stdout.splitlines():
    FAILS.append(f"cli hole ASK line format:\n{ran.stdout}")
RAN.append("cli Evals case ASK line format")
ran = run_cli(slot("Evals", "- Evals: Pass: keep a row."))
if "ASK: Evals: Is there a pass case and a fail case here?" not in ran.stdout.splitlines() or ran.returncode != 2:
    FAILS.append(f"cli Evals case ASK line format:\n{ran.stdout}")


# A should pass or should fail phrase with a blank body is not a case, so a leading phrase adds no empty case.
LEAD = "Should fail if the email is missing. A signed form should pass, a blank form should fail."
RAN.append("a leading phrase with nothing before it is not a case")
if [(kind, body.strip(" ,.")) for kind, body in eval_cases(LEAD)] != [
        ("pass", "if the email is missing. A signed form"), ("fail", "a blank form")]:
    FAILS.append(f"a leading phrase with nothing before it is not a case: {eval_cases(LEAD)}")
expect_outcome("a leading phrase beside a pass and a fail case passes", slot("Evals", f"- Evals: {LEAD}"), "pass")
expect_outcome("a leading should pass is no pass case; asks, not fails",
               slot("Evals", "- Evals: Should pass if the form is signed. A blank form should fail."), "ask")


if __name__ == "__main__":
    for f in FAILS:
        print(f"FAIL {f}")
    print(f"{len(RAN) - len(FAILS)}/{len(RAN)} passed")
    sys.exit(1 if FAILS else 0)
