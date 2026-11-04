"""Run: python3 check/test_check.py"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

PRD = "Agents can edit an order's condition. Edits are sent to the client's CRM every night.\n"

BLOCK = """### Questions from engineering (Dana, Jan 2026)

Please answer under each question.

One term used below:
- **Shared details.** Details both sides can edit. The PRD calls them Writable.

**Biggest decisions**

**1.** An agent edits an order. The client edits it the same day. Whose edit should stay?

**Smaller questions, by topic**

Purpose

**2.** What customer problem does this solve?
"""

QUESTIONS = """PM | Whose edit should stay? | which side wins a same-day edit | We would guess whose edit the agent sees the next day
PM | What customer problem does this solve? | the purpose | We would guess which customers the feature is for
DESIGN-DOC | How do we convert time zones? | time zone handling | engineering call
ANSWERED | When are edits sent? | send timing | Edits are sent to the client's CRM every night.
"""


def run_cmd(cmd, *files):
    """files are (name, text) pairs, or a name alone for a file that is not written."""
    d = tempfile.mkdtemp()
    paths = []
    for f in files:
        name, text = f if isinstance(f, tuple) else (f, None)
        p = os.path.join(d, name)
        if text is not None:
            open(p, "w").write(text)
        paths.append(p)
    out = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), cmd, *paths], capture_output=True, text=True)
    return out.stdout


def run(prd, questions, block=BLOCK):
    return run_cmd("sort", ("prd.md", prd), ("questions.txt", questions), ("open-questions.md", block))


CARRY_GAPS = """GAP 1: R1 | Whose edit stays? | PM | not stated
GAP 2: R2 | Does "nightly" mean the client's night or ours? | Unclear wording | not stated
GAP 3: R3 | How are time zones stored? | Engineer | not stated
"""
CARRIED = "GAP 1 | Whose edit should stay?\nGAP 2 | When are edits sent?\n"


def carry(carried, questions=QUESTIONS):
    return run_cmd("carry", ("gaps.txt", CARRY_GAPS), ("questions.txt", questions), ("carried.txt", carried))


PREMISE = """Whose edit should stay? | order status | app/Order.php:12
What customer problem does this solve? | none | none
"""

TERMS_PRD = "Acme sends each customer's edits to the customer's CRM. Acme logs them. The client's CRM is updated. Helpdesk keeps it.\n"
TERMS = "product | Acme | Helpdesk\ncustomer | customer | client\n"
CLEAN_BLOCK = BLOCK.replace("The client edits it", "The customer edits it")


def premise(p, block=BLOCK):
    return run_cmd("premise", ("premise.txt", p), ("open-questions.md", block))


def terms(t, prd=TERMS_PRD, block=CLEAN_BLOCK):
    return run_cmd("terms", ("prd.md", prd), ("terms.txt", t) if t is not None else "terms.txt", ("open-questions.md", block))


OPEN = """### Questions from engineering (Dana, Jan 2026)

Please answer under each question.

Two terms used below:
- **Shared details.** Details both sides can edit. The PRD calls them Writable.
- **Who wins.** The rule when both sides change the same detail.

**Biggest decisions**

**1.** A customer edits an order and the client edits it the same day. Whose edit should stay?

**Smaller questions, by topic**

History

**2.** Someone without send permission edits an order, marked "Not sent" (the PRD calls it "Not pushed"). How should it be sent?
"""


def open_questions(text, labels=None):
    files = [("open-questions.md", text)]
    if labels is not None:
        files.append(("prd-labels.txt", labels))
    return run_cmd("open-questions", *files)


def pm_list(block):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "rules"))
    open(os.path.join(d, "rules", "prd-basics.json"), "w").write(
        '{"name": "prd-basics", "type": "prd-questions", "questions": ["What customer problem does this solve?"]}')
    open(os.path.join(d, "open-questions.md"), "w").write(block)
    out = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), "pm-list",
                          os.path.join(d, "open-questions.md"), os.path.join(d, "rules")], capture_output=True, text=True)
    return out.stdout


DEFER_PRD = PRD + "CRM edits reach Acme nightly; cadence is TBD with engineering.\n"
DEFER_SCENARIO = "SCENARIO 1: sync | How soon must a CRM edit show in Acme? | cadence is TBD with engineering.\n"
DEFER_GAP = "GAP 1: R2 | How soon must a CRM edit show in Acme? | PM | cadence is TBD with engineering.\n"


def gaps(g):
    return run_cmd("gaps", ("prd.md", DEFER_PRD), ("gaps.txt", g))


def expect(name, out, first):
    ok = out.startswith(first)
    print(f"{'ok ' if ok else 'BAD'} {name}")
    if not ok:
        print(out)
    return ok


def fresh(now, then=PRD):
    return run_cmd("fresh", ("prd.md", then), ("prd-now.md", now))


def exit_code(cmd, text):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "file.md")
    open(p, "w").write(text)
    return f"exit {subprocess.run([sys.executable, os.path.join(HERE, 'check.py'), cmd, p], capture_output=True).returncode}"


def usage(*args):
    out = subprocess.run([sys.executable, os.path.join(HERE, "check.py"), *args], capture_output=True, text=True)
    return f"exit {out.returncode} {(out.stdout + out.stderr).splitlines()[0]}"


SCORE_KEY = """| ID | Point | Question | Owner | PRD evidence |
|----|-------|----------|-------|--------------|
| G01 | R1 | Whose edit stays? | PM | not stated |
| G02 | R2 | What if the send fails? | Engineer | not stated |
| G03 | PM unsure | Does the CRM confirm a send? | Engineer | "I think the CRM confirms it." |
"""
SCORE_GAPS = """GAP 1: R1 | When both sides edit, whose edit stays? | PM | not stated
GAP 2: R2 | Which fields are sent? | PM | not stated
GAP 3: U1 | Does the CRM confirm a send? | Engineer | I think the CRM confirms it.
"""


def score(key, gaps_text=SCORE_GAPS):
    d = tempfile.mkdtemp()
    k, g = os.path.join(d, "key.md"), os.path.join(d, "gaps.txt")
    open(k, "w").write(key)
    open(g, "w").write(gaps_text)
    out = subprocess.run([sys.executable, os.path.join(HERE, "score_case.py"), k, g], capture_output=True, text=True)
    return " ".join(line.split()[0] for line in out.stdout.splitlines() if " found" in line) + " | " + out.stdout.splitlines()[-1]


PURPOSE_FIRST = BLOCK.replace("**1.** An agent edits an order. The client edits it the same day. Whose edit should stay?",
                              "**1.** What customer problem does this solve?").replace(
    "**2.** What customer problem does this solve?", "**2.** An agent edits an order. Whose edit should stay?")

results = [
    expect("sorted list passes", run(PRD, QUESTIONS), "PASS sort: 4 questions, 2 PM"),
    expect("design-doc question in the block fails",
           run(PRD, QUESTIONS.replace("PM | Whose", "DESIGN-DOC | Whose")), "FAIL sort"),
    expect("PM reason that names no guess fails",
           run(PRD, QUESTIONS.replace("We would guess which customers the feature is for", "scope of every later call")), "FAIL sort"),
    expect("ANSWERED without a PRD quote fails",
           run(PRD, QUESTIONS.replace("Edits are sent to the client's CRM every night.", "Edits are sent weekly.")), "FAIL sort"),
    expect("PM row without a reason fails",
           run(PRD, QUESTIONS.replace("| We would guess which customers the feature is for", "|")), "FAIL sort"),
    expect("block question with no row fails",
           run(PRD, QUESTIONS.replace("PM | What customer problem does this solve? | the purpose | We would guess which customers the feature is for\n", "")),
           "FAIL sort"),
    expect("ANSWERED by two PRD quotes passes",
           run(PRD, QUESTIONS.replace("Edits are sent to the client's CRM every night.",
                                      "Agents can edit an order's condition. + Edits are sent to the client's CRM every night.")), "PASS sort"),
    expect("ANSWERED with one invented quote of two fails",
           run(PRD, QUESTIONS.replace("Edits are sent to the client's CRM every night.",
                                      "Agents can edit an order's condition. + Edits are sent weekly.")), "FAIL sort"),
    expect("premise rows for every question pass", premise(PREMISE), "PASS premise: 2 questions checked"),
    expect("ambiguous noun fails",
           premise(PREMISE.replace("app/Order.php:12", "ambiguous: typed field at form.php:3; saved date at Ticket.php:9")),
           "FAIL premise"),
    expect("rewritten question with no premise rows fails",
           premise(PREMISE, BLOCK.replace("Whose edit should stay?", "Whose edit should we keep?")), "FAIL premise"),
    expect("PRD's own terms pass", terms(TERMS), "PASS terms: product Acme 2, customer customer 2"),
    expect("missing terms file fails", terms(None), "FAIL terms"),
    expect("less common term fails", terms("product | Helpdesk | Acme\ncustomer | customer | client\n"), "FAIL terms"),
    expect("missing customer row fails", terms("product | Acme | Helpdesk\n"), "FAIL terms"),
    expect("other name in the block fails", terms(TERMS, block=BLOCK), "FAIL terms"),
    expect("template block passes", open_questions(OPEN), "PASS open-questions: 2 terms, 1 biggest, 2 questions"),
    expect("PRD label inside 'the PRD calls it' passes", open_questions(OPEN, "Not pushed\n"), "PASS open-questions"),
    expect("PRD label in a question fails", open_questions(OPEN.replace("Whose edit", "Whose Writable edit"), "Writable\n"),
           "FAIL open-questions"),
    expect("markdown list numbering fails", open_questions(OPEN.replace("**1.** ", "- 1. ")), "FAIL open-questions"),
    expect("proposed answer fails", open_questions(OPEN.replace("should stay?", "should stay? Proposed: keep the newest.")),
           "FAIL open-questions"),
    expect("point number fails", open_questions(OPEN.replace("should stay?", "should stay? (R12)")), "FAIL open-questions"),
    expect("reading guidance in the intro fails",
           open_questions(OPEN.replace("Please answer under each question.", "Please answer under each question. Start with 1.")),
           "FAIL open-questions"),
    expect("a list with no glossary passes", open_questions(re.sub(r"Two terms used below:\n(- \*\*[^\n]*\n)+\n", "", OPEN)), "PASS open-questions: 0 terms"),
    expect("a test plan with no questions passes", open_questions("### Test plan questions from engineering (Dana, Jan 2026)\n\nNo questions.\n"), "PASS open-questions: 0 terms, 0 biggest, 0 questions"),
    expect("a test plan heading passes", open_questions(OPEN.replace("### Questions from engineering", "### Test plan questions from engineering")), "PASS open-questions"),
    expect("another heading fails", open_questions(OPEN.replace("### Questions from engineering", "### Notes from engineering")), "FAIL open-questions"),
    expect("missing biggest group fails", open_questions(OPEN.replace("**Biggest decisions**\n", "")), "FAIL open-questions"),
    expect("more than 20 questions pass, there is no cap",
           open_questions(OPEN + "".join(f"\n**{i}.** Should case {i} stay?\n" for i in range(3, 26))), "PASS open-questions"),
    expect("purpose question first passes", pm_list(PURPOSE_FIRST), "PASS pm-list: 2 questions"),
    expect("purpose question not first fails", pm_list(BLOCK), "FAIL pm-list"),
    expect("two questions with the same ask fail",
           pm_list(PURPOSE_FIRST + "\n**3.** The customer edits it too. Whose edit should stay?\n"), "FAIL pm-list"),
    expect("three related asks in one question pass",
           pm_list(PURPOSE_FIRST + "\n**3.** Acme keeps a record of what it sends. How long should it keep it? Should anyone else see it? Should admins download it?\n"),
           "PASS pm-list"),
    expect("four asks in one question fail",
           pm_list(PURPOSE_FIRST + "\n**3.** Acme keeps a record. How long? Who sees it? Can admins download it? Can they delete it?\n"),
           "FAIL pm-list"),
    expect("a question past the word limit fails",
           pm_list(PURPOSE_FIRST + "\n**3.** " + "Today the admin opens the import page and sees a long list of details that came in from the CRM. " * 3 + "Should those details stay?\n"),
           "FAIL pm-list"),
    expect("more than one meeting's worth passes with a warning",
           pm_list(PURPOSE_FIRST + "".join(f"\n**{i}.** Should case {i} stay?\n" for i in range(3, 27))),
           "PASS pm-list: 26 questions\nWARN"),
    expect("put-off scenario answer with its gap passes", gaps(DEFER_SCENARIO + DEFER_GAP), "PASS gaps: 1 checked"),
    expect("put-off scenario answer without a gap fails", gaps(DEFER_SCENARIO), "FAIL gaps"),
    expect("every PM and Unclear wording gap carried passes", carry(CARRIED), "PASS carry: 2 PM or Unclear wording gaps"),
    expect("a PM gap carried nowhere fails", carry("GAP 2 | When are edits sent?\n"), "FAIL carry"),
    expect("a gap carried to a question not in questions.txt fails", carry(CARRIED.replace("When are edits sent?", "Who reads the log?")), "FAIL carry"),
    expect("a gap carried to a DROP row passes", carry(CARRIED.replace("When are edits sent?", "Who reads the log?"), QUESTIONS + "DROP | Who reads the log? | log readers | duplicate of Q1\n"), "PASS carry"),
    expect("the same PRD is fresh", fresh(PRD), "PASS fresh: 2 sentences in the PRD now, 0 changed"),
    expect("spacing and list markers are not a change", fresh("- Agents  can edit an order's condition.\n\nEdits are sent to the client's CRM every night.\n"), "PASS fresh"),
    expect("a PRD edited since the review fails with both lines",
           fresh(PRD.replace("every night", "every hour")),
           "FAIL fresh: 2 sentences in the PRD now, 2 changed\n  removed: Edits are sent to the client's CRM every night.\n  added: Edits are sent to the client's CRM every hour."),
    expect("a writing failure exits 1", exit_code("writing", "The risk is old data \u2014 it wins.\n"), "exit 1"),
    expect("clean writing exits 0", exit_code("writing", "Old data can overwrite new data.\n"), "exit 0"),
    expect("-h prints usage", usage("-h"), "exit 0 Deterministic checks"),
    expect("no command prints usage", usage(), "exit 2 Deterministic checks"),
    expect("unknown command prints usage", usage("nope", "a"), "exit 2 Deterministic checks"),
    expect("a missing argument prints usage", usage("sort", "prd.md"), "exit 2 Deterministic checks"),
    expect("score without Terms passes any gap on the point", score(SCORE_KEY), "G01 G02 G03 | PASS 3/3"),
    expect("Terms fail a gap on the point about a different problem",
           score(SCORE_KEY + "Terms: G02 | fail\n"), "G01 G03 | FAIL 2/3"),
    expect("a/b Terms match either word", score(SCORE_KEY + "Terms: G01 | whose edit/who wins\n"), "G01 G02 G03 | PASS"),
    expect("PM unsure matches a U point", score(SCORE_KEY, SCORE_GAPS.replace("I think the CRM confirms it.", "not stated")),
           "G01 G02 G03 | PASS"),
    expect("a gap off the point that quotes the evidence is on target",
           score(SCORE_KEY, SCORE_GAPS.replace("GAP 3: U1", "GAP 3: R9")), "G01 G02 G03 | PASS"),
    expect("a gap off the point and its quote is missed",
           score(SCORE_KEY, SCORE_GAPS.replace("GAP 3: U1", "GAP 3: R9").replace("I think the CRM confirms it.", "not stated")),
           "G01 G02 | FAIL 2/3"),
]
sys.exit(0 if all(results) else 1)
