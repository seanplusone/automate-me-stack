"""Run: python3 check/test_check_edd.py"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "..", "rules", "edd-sections.json")

DELTA = """DELTA D1: app | CURRENT NONE | CHANGE queue a row | BECAUSE R1 | UNDER A1
ENABLE E1: scope the job | ENABLES R1 | NEEDED BECAUSE CS1 | UNDER A1
"""

GOOD_DIAGRAMS = """## Architecture

```mermaid
flowchart LR
  App -->|D1 queue row| Outbox
  Outbox -->|E1 per customer| Job
```

```mermaid
sequenceDiagram
  participant App
  participant Job
  App->>Job: D1 queue row
  Job-->>App: E1 done
```

## Data model
"""

HAZARDS = """## Known hazards

| # | Hazard | Evidence | Level | Mitigation |
|---|---|---|---|---|
| 1 | CRM hides failures | {ev} | {lv} | Check the reply |
"""

RAN = """ID: SPIKE1
STATUS: RAN
QUESTION: Does CRM report a rejected update?
METHOD: python3 spike1.py
WHERE: sandbox layer
RESULT: {"success": false}
ANSWER: Yes, per feature.
LEVEL: 4
"""

PLANNED = """ID: SPIKE1
STATUS: PLANNED
QUESTION: Does the service report a rejected update?
METHOD: python3 spike1.py
WHERE: sandbox layer
"""

BLOCKED = """ID: SPIKE1
STATUS: BLOCKED
BLOCKED: No sandbox CRM account is named in sandbox.md.
QUESTION: Does CRM report a rejected update?
"""


def run(*args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "check_edd.py"), *args], capture_output=True, text=True)
    return r.stdout.strip()


def case(edd, files):
    d = tempfile.mkdtemp()
    ev = os.path.join(d, "evidence")
    os.mkdir(ev)
    for name, text in files.items():
        open(os.path.join(ev, name), "w").write(text)
    open(os.path.join(d, "edd.md"), "w").write(edd)
    open(os.path.join(d, "delta.txt"), "w").write(DELTA)
    return os.path.join(d, "edd.md"), ev, os.path.join(d, "delta.txt")


def expect(name, got, want):
    if got != want:
        print(f"FAIL {name}\n  want: {want!r}\n  got:  {got!r}")
        return 1
    print(f"ok   {name}")
    return 0


bad = 0

edd, ev, delta = case(GOOD_DIAGRAMS + HAZARDS.format(ev="SPIKE1", lv="4"), {"SPIKE1.md": RAN})
bad += expect("ran spike backs level 4", run("spikes", edd, ev, RULES), "PASS spikes: 1 cited, 1 ran")
bad += expect("both diagrams cover the delta list", run("diagrams", edd, delta, RULES),
              "PASS diagrams: 2 found, 2/2 delta ids drawn")

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1, CS1", lv="2"), {"SPIKE1.md": BLOCKED})
bad += expect("blocked spike with a reason passes", run("spikes", edd, ev, RULES), "PASS spikes: 1 cited, 0 ran")

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1", lv="4"), {"SPIKE1.md": BLOCKED})
bad += expect("blocked spike cannot back level 4", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran\n  hazard 1 claims level 4 but cites no PROBE or SPIKE that ran")

edd, ev, delta = case(HAZARDS.format(ev="SPIKE2", lv="2"), {"SPIKE1.md": RAN})
bad += expect("cited spike with no file", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran\n  SPIKE2 is cited but has no evidence file")

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1", lv="2"), {"SPIKE1.md": "ID: SPIKE1\nSTATUS: BLOCKED\nBLOCKED: no\n"})
bad += expect("blocked with no real reason", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran\n  SPIKE1 is blocked with no reason")

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1", lv="4"), {"SPIKE1.md": RAN.replace("sandbox layer", "production layer")})
bad += expect("spike against production", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 1 ran\n  SPIKE1 ran against production or a customer: production layer")

only_flow = GOOD_DIAGRAMS.split("```mermaid\nsequenceDiagram")[0] + "## Data model\n"
edd, ev, delta = case(only_flow.replace("E1 per customer", "D9 per customer"), {})
bad += expect("missing sequence diagram, missing and unknown ids", run("diagrams", edd, delta, RULES),
              "FAIL diagrams: 1 found, 1/2 delta ids drawn\n  no sequenceDiagram diagram in Architecture\n"
              "  E1 is in the delta list but in no diagram\n  D9 is in a diagram but not in the delta list")

edd, ev, delta = case(GOOD_DIAGRAMS.replace("  participant Job\n", ""), {})
bad += expect("undeclared participant", run("diagrams", edd, delta, RULES),
              "FAIL diagrams: 2 found, 2/2 delta ids drawn\n  sequence diagram uses undeclared participant: Job")

# ---- layout roles, several tables in one section ----

TEAM_LAYOUT = {
    "header": ["Status"],
    "sections": ["Summary", "Risks and Open Questions"],
    "tables": {"Risks and Open Questions": [["#", "Hazard", "Evidence", "Level", "Mitigation"],
                                            ["#", "Question", "Position", "Owner", "By", "Blocks"]]},
    "roles": {"hazards": "Risks and Open Questions", "decisions": "Risks and Open Questions"},
    "diagrams": {"section": "Summary", "kinds": ["flowchart"]},
}

TEAM_EDD = """Status: Draft

## Summary

C1 the PRD says X. The code does Y. OPEN. The design assumes Y.

## Risks and Open Questions

| # | Hazard | Evidence | Level | Mitigation |
|---|---|---|---|---|
| 1 | Sends fail quietly | a.php:10 | 2 | Check the reply |

| # | Question | Position | Owner | By | Blocks |
|---|---|---|---|---|---|
| 1 | GAP 5 which clock wins | Use the app clock. D1 | PM | 2026-11-01 | D1 |
"""


def tmp(files):
    d = tempfile.mkdtemp()
    for name, text in files.items():
        os.makedirs(os.path.dirname(os.path.join(d, name)), exist_ok=True)
        open(os.path.join(d, name), "w").write(text)
    return d


def layout_case(edd, layout=TEAM_LAYOUT):
    d = tmp({"edd.md": edd, "layout.json": json.dumps(layout)})
    return os.path.join(d, "edd.md"), os.path.join(d, "layout.json")


edd, lay = layout_case(TEAM_EDD)
bad += expect("two tables in one section both match", run("sections", edd, lay), "PASS sections: 2 expected")
bad += expect("hazards table is the second kind of table found by its columns", run("hazards", edd, lay), "PASS hazards: 1 rows")

edd, lay = layout_case(TEAM_EDD.replace("| Blocks |", "| Other |"))
bad += expect("second table lacks a column", run("sections", edd, lay),
              "FAIL sections: 2 expected\n  table 'Risks and Open Questions' missing column: Blocks (table 2)")

edd, lay = layout_case(TEAM_EDD.replace("| # | Hazard | Evidence | Level | Mitigation |\n|---|---|---|---|---|\n| 1 | Sends fail quietly | a.php:10 | 2 | Check the reply |\n", ""))
bad += expect("no hazards table in the role's section", run("hazards", edd, lay), "FAIL hazards: 0 rows\n  no hazards table")

# ---- corrections, ASSUMES, decisions rows ----

MAP = "BRANCH: app\n  R1: save sends\n"
GAPS = "GAP 1: R1 | q | Engineer | n\nGAP 5: R1 | which clock | PM | n\nGAP 6: R1 | who deletes | PM | n\n"
ARCH = "ARCH A1: queue | SERVES R1\n"
CURRENT = "STEP CS1: save | a.php:1 | x\n"
ANSWERS = """ANSWER GAP 6: who deletes | "Admins." | 2026-10-13
PENDING GAP 5: which clock wins | asked 2026-10-13
CORRECTION C1: "the pull is instant" | the pull runs hourly, a.php:10 | posted 2026-10-14 | OPEN
"""
DELTAS = """DELTA D1: app | CURRENT NONE | CHANGE queue a row | BECAUSE R1 | ASSUMES GAP 5 | UNDER A1
ENABLE E1: scope the job | ENABLES R1 | NEEDED BECAUSE CS1 | UNDER A1
"""


def delta_case(deltas=DELTAS, answers=ANSWERS, evidence=None):
    files = {"map.txt": MAP, "gaps.txt": GAPS, "answers.md": answers, "arch.txt": ARCH, "current.txt": CURRENT,
             "delta.txt": deltas}
    files.update({f"evidence/{k}": v for k, v in (evidence or {}).items()})
    d = tmp(files)
    ev = [os.path.join(d, "evidence", k) for k in (evidence or {})]
    return run("delta", *[os.path.join(d, f) for f in ("delta.txt", "map.txt", "gaps.txt", "answers.md", "arch.txt", "current.txt")], *ev)


bad += expect("ASSUMES a PENDING GAP and a good CORRECTION pass", delta_case(), "PASS delta: 2 changes checked")
bad += expect("CORRECTION with no file:line",
              delta_case(answers=ANSWERS.replace("a.php:10", "somewhere")),
              "FAIL delta: 2 changes checked\n  C1 has no file:line for what the code does")
bad += expect("CORRECTION with a bad status",
              delta_case(answers=ANSWERS.replace("| OPEN", "| MAYBE")),
              "FAIL delta: 2 changes checked\n  C1 status must be OPEN, ACCEPTED or REJECTED: MAYBE")
bad += expect("ASSUMES an answered GAP",
              delta_case(DELTAS.replace("ASSUMES GAP 5", "ASSUMES GAP 6")),
              "FAIL delta: 2 changes checked\n  D1 ASSUMES GAP 6, which is answered, drop ASSUMES")
bad += expect("ASSUMES an unknown GAP",
              delta_case(DELTAS.replace("ASSUMES GAP 5", "ASSUMES GAP 9")),
              "FAIL delta: 2 changes checked\n  D1 ASSUMES is not a PENDING GAP or a planned or blocked spike: GAP 9")
bad += expect("ASSUMES a planned spike",
              delta_case(DELTAS.replace("ASSUMES GAP 5", "ASSUMES SPIKE1"), evidence={"SPIKE1.md": PLANNED}),
              "PASS delta: 2 changes checked")
bad += expect("ASSUMES a spike that ran",
              delta_case(DELTAS.replace("ASSUMES GAP 5", "ASSUMES SPIKE1"), evidence={"SPIKE1.md": RAN}),
              "FAIL delta: 2 changes checked\n  D1 ASSUMES SPIKE1, which ran, drop ASSUMES")


def coverage_case(edd, deltas=DELTAS, answers=ANSWERS, evidence=None):
    files = {"edd.md": edd, "map.txt": MAP, "gaps.txt": GAPS, "answers.md": answers, "arch.txt": ARCH,
             "delta.txt": deltas, "layout.json": json.dumps(TEAM_LAYOUT)}
    files.update({f"evidence/{k}": v for k, v in (evidence or {}).items()})
    d = tmp(files)
    ev = [os.path.join(d, "evidence", k) for k in (evidence or {})]
    return run("coverage", *[os.path.join(d, f) for f in ("edd.md", "map.txt", "gaps.txt", "answers.md", "layout.json")],
               os.path.join(d, "arch.txt"), os.path.join(d, "delta.txt"), *ev)


COVERED = """Status: Draft

## Summary

[R1] [GAP 1] [A1] [D1] [E1] C1 the PRD says X. The code does Y. OPEN. The design assumes Y.

## Risks and Open Questions

| # | Question | Position | Owner | By | Blocks |
|---|---|---|---|---|---|
| 1 | GAP 5 which clock wins | Use the app clock | PM | 2026-11-01 | D1 |
"""

bad += expect("pending GAP, correction and deltas all covered", coverage_case(COVERED), "PASS coverage: 7/7 cited")
bad += expect("CORRECTION not cited in the prd_record section",
              coverage_case(COVERED.replace("C1 the PRD", "the PRD")),
              "FAIL coverage: 6/7 cited\n  C1 is not listed in Summary")
bad += expect("OPEN CORRECTION does not say what the design assumes",
              coverage_case(COVERED.replace("The design assumes Y.", "")),
              "FAIL coverage: 7/7 cited\n  C1 is OPEN but its line in Summary does not say what the design assumes")
bad += expect("decisions row omits the D id that ASSUMES the GAP",
              coverage_case(COVERED.replace("| D1 |", "| none |")),
              "FAIL coverage: 7/7 cited\n  the Risks and Open Questions row for GAP 5 does not list D1, which ASSUMES GAP 5")
bad += expect("PENDING GAP cited only outside the decisions section",
              coverage_case(COVERED.replace("| 1 | GAP 5 which clock wins |", "| 1 | which clock wins |").replace("[R1]", "[R1] [GAP 5]")),
              "FAIL coverage: 6/7 cited\n  no row in Risks and Open Questions cites GAP 5")

SPIKE_DELTAS = DELTAS.replace("ASSUMES GAP 5", "ASSUMES SPIKE1")
SPIKE_ROW = "| 2 | SPIKE1 spike: does the service report a rejected update | Run it | PM | 2026-11-01 | D1 |"
bad += expect("planned spike row names D1 and says spike",
              coverage_case(COVERED + SPIKE_ROW + "\n", SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED}),
              "PASS coverage: 7/7 cited")
bad += expect("planned spike row omits D1",
              coverage_case(COVERED + SPIKE_ROW.replace("| D1 |", "| none |") + "\n", SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED}),
              "FAIL coverage: 7/7 cited\n  the Risks and Open Questions row for SPIKE1 does not list D1, which ASSUMES SPIKE1")
bad += expect("planned spike row does not say it is a spike",
              coverage_case(COVERED + SPIKE_ROW.replace(" spike:", ":") + "\n", SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED}),
              "FAIL coverage: 7/7 cited\n  the Risks and Open Questions row for SPIKE1 does not say it is a spike")
bad += expect("planned spike with no row",
              coverage_case(COVERED, SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED}),
              "FAIL coverage: 7/7 cited\n  no row in Risks and Open Questions cites SPIKE1")
SHARED = COVERED.replace("GAP 5 which clock wins", "GAP 5 which clock wins, SPIKE1 spike")
bad += expect("planned spike answering a PENDING GAP shares its row",
              coverage_case(SHARED, SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED + "ANSWERS: GAP 5\n"}),
              "PASS coverage: 7/7 cited")
bad += expect("shared row must say spike",
              coverage_case(SHARED.replace("SPIKE1 spike", "SPIKE1"), SPIKE_DELTAS, evidence={"SPIKE1.md": PLANNED + "ANSWERS: GAP 5\n"}),
              "FAIL coverage: 7/7 cited\n  the Risks and Open Questions row for GAP 5 and SPIKE1 does not say it is a spike")

# ---- planned spikes ----

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1, CS1", lv="2"), {"SPIKE1.md": PLANNED})
bad += expect("planned spike passes and is counted", run("spikes", edd, ev, RULES), "PASS spikes: 1 cited, 0 ran, 1 planned")
edd, ev, delta = case(HAZARDS.format(ev="SPIKE1", lv="4"), {"SPIKE1.md": PLANNED})
bad += expect("planned spike cannot back level 4", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran, 1 planned\n  hazard 1 claims level 4 but cites no PROBE or SPIKE that ran")
edd, ev, delta = case(HAZARDS.format(ev="SPIKE1, CS1", lv="2"), {"SPIKE1.md": PLANNED + "RESULT: it worked\n"})
bad += expect("planned spike with a result", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran, 1 planned\n  SPIKE1 is planned but has a RESULT")
edd, ev, delta = case(HAZARDS.format(ev="SPIKE1, CS1", lv="2"), {"SPIKE1.md": PLANNED.replace("METHOD: python3 spike1.py\n", "")})
bad += expect("planned spike with no method", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 0 ran, 1 planned\n  SPIKE1 is planned but has no METHOD")

# ---- evidence fields, levels, production guard, standalone check ----

OK_RAN = "ID: PROBE1\nSTATUS: RAN\nQUESTION: q\nMETHOD: read a.php\nWHERE: staging-app, code reading only\nRESULT: a.php:3 says x\nANSWER: yes\nLEVEL: 2\n"
PASS1 = "PASS spikes: 1 cited, 1 ran"

edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("RESULT: a.php:3 says x\n", "RESULT:\n  a.php:3 says x\n  more\n")})
bad += expect("RESULT on following lines counts", run("spikes", edd, ev, RULES), PASS1)

edd, ev, delta = case(HAZARDS.format(ev="SPIKE1", lv="2"), {"SPIKE1.md": OK_RAN.replace("PROBE1", "SPIKE1 (PROJ-2 P0-3)")})
bad += expect("ID with a suffix is its first token", run("spikes", edd, ev, RULES), PASS1)

edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("LEVEL: 2", "LEVEL: 3 (walked the path)")})
bad += expect("LEVEL with text is its leading digit", run("spikes", edd, ev, RULES), PASS1)

edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN})
bad += expect("level 2 RAN probe passes", run("spikes", edd, ev, RULES), PASS1)
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("LEVEL: 2", "LEVEL: 1")})
bad += expect("level 1 RAN probe fails", run("spikes", edd, ev, RULES), "FAIL spikes: 1 cited, 1 ran\n  PROBE1 ran but LEVEL is not 2 to 5: 1")

edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="4"), {"PROBE1.md": OK_RAN})
bad += expect("hazard level 4 citing only a level 2 probe fails", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 1 ran\n  hazard 1 claims level 4 but the PROBEs and SPIKEs it cites ran at level 2 at most")
edd, ev, delta = case(HAZARDS.format(ev="PROBE1, SPIKE1", lv="4"), {"PROBE1.md": OK_RAN, "SPIKE1.md": RAN})
bad += expect("hazard level 4 passes when one cited file ran at 4", run("spikes", edd, ev, RULES), "PASS spikes: 2 cited, 2 ran")

edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("code reading only", "No customer or live URL, never a customer org, never production")})
bad += expect("negated customer phrases pass", run("spikes", edd, ev, RULES), PASS1)
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("code reading only", "not a production or a customer system")})
bad += expect("a negated list passes", run("spikes", edd, ev, RULES), PASS1)
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace("code reading only", "no production, but the customer db")})
bad += expect("a customer that is not negated still fails", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 1 ran\n  PROBE1 ran against production or a customer: staging-app, no production, but the customer db")

PROD_WHERE = "WHERE: staging-app, code reading only"
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace(PROD_WHERE, "WHERE: production read replica, read-only")})
bad += expect("production without RUNNER fails", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 1 ran\n  PROBE1 ran against production or a customer: production read replica, read-only")
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace(PROD_WHERE, "WHERE: production read replica, read-only") + "RUNNER: person\n"})
bad += expect("production with RUNNER person and read-only passes, as person-run", run("spikes", edd, ev, RULES),
              "PASS spikes: 1 cited, 1 ran, 1 person-run")
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": OK_RAN.replace(PROD_WHERE, "WHERE: production read replica") + "RUNNER: person\n"})
bad += expect("production with RUNNER person but not read-only fails", run("spikes", edd, ev, RULES),
              "FAIL spikes: 1 cited, 1 ran, 1 person-run\n  PROBE1 ran against production or a customer: production read replica")
edd, ev, delta = case(HAZARDS.format(ev="PROBE1", lv="2"), {"PROBE1.md": PLANNED.replace("PROBE1", "PROBE1").replace("SPIKE1", "PROBE1").replace("sandbox layer", "production replica, read-only") + "RUNNER: person\n"})
bad += expect("planned production probe run by a person passes", run("spikes", edd, ev, RULES),
              "PASS spikes: 1 cited, 0 ran, 1 planned, 1 person-run")

_, ev, _ = case("", {"PROBE1.md": OK_RAN, "SPIKE1.md": PLANNED, "SPIKE2.md": BLOCKED.replace("SPIKE1", "SPIKE2")})
bad += expect("evidence checks a dir with no EDD", run("evidence", ev), "PASS evidence: 3 files, 1 ran, 1 planned")
_, ev, _ = case("", {"PROBE1.md": OK_RAN.replace("LEVEL: 2", "LEVEL: 9"), "SPIKE1.md": PLANNED + "RESULT: x\n"})
bad += expect("evidence reports each failing file", run("evidence", ev),
              "FAIL evidence: 2 files, 1 ran, 1 planned\n  PROBE1 ran but LEVEL is not 2 to 5: 9\n  SPIKE1 is planned but has a RESULT")

# ---- current and blast: every cited file:line and quote must be real ----

MODEL_PHP = """<?php
class Report extends Model {
    protected static function boot() {
        static::saved(function ($r) { $r->touch(); });
    }
}
"""
JOB_PHP = "<?php\nclass SyncJob {\n    public function handle() {\n        Report::where('id', 1)->update(['x' => 1]);\n    }\n}\n"

BLAST = """ROOTS: {root}
ENTITY: Report | app/Model.php
CHAIN: Model | app/Model.php
HOOK BR1: saved | app/Model.php:4 | "static::saved(function ($r) { $r->touch(); });" | touches the report
SCOPE BR2: tenant | app/Model.php:3 | "protected static function boot() {" | filters by instance
WRITER BR3: app/Model.php:4 | "$r->touch();" | updates the timestamp
READER BR4: app/Model.php:2 | "class Report extends Model {" | reads the class
NOT FOUND: observers | grep -rn Observer app
SEARCHES: grep -rn saved app
COUNTS: hooks 1, scopes 1, writers 1, readers 1, not found 1
"""

CURRENT_TXT = """ROOTS: {root}
BRANCH: save
STEP CS1: 1 | app/Model.php:4 | "static::saved(function ($r) {" | the save hook fires
STEP CS2: 2 | app/Model.php:4 | "$r->touch();" | the hook touches the row
NONE: delete | grep -rn delete app
SEARCHES: grep -rn saved app
COUNTS: branches 2, steps 2, none 1, pm questions 0
"""


def repo_case(text, files=None, extra_root=None):
    """Make a repo with the cited files, fill {root} in text, and return (roots, path to the checked file)."""
    d = tmp({f: c for f, c in (files or {"app/Model.php": MODEL_PHP}).items()})
    roots = d if extra_root is None else f"{d},{extra_root}"
    path = os.path.join(d, "out.txt")
    open(path, "w").write(text.replace("{root}", roots))
    return roots, path


def check_cited(sub, text, files=None, extra_root=None):
    roots, path = repo_case(text, files, extra_root)
    return run(sub, roots, path), roots


got, _ = check_cited("blast", BLAST)
bad += expect("blast: well-formed list passes", got, "PASS blast: 4 items checked")
got, _ = check_cited("current", CURRENT_TXT)
bad += expect("current: well-formed trace passes", got, "PASS current: 2 items checked")
got, _ = check_cited("blast", CURRENT_TXT)
bad += expect("a CS id names the report current whichever subcommand ran", got, "PASS current: 2 items checked")
got, _ = check_cited("blast", "ROOTS: x\nSEARCHES: none\nCOUNTS: hooks 0\n")
bad += expect("blast: no cited items passes with zero", got, "PASS blast: 0 items checked")

got, _ = check_cited("blast", BLAST.replace('app/Model.php:3 | "protected static function boot() {"', 'app/Model.php:3 | "protected static   function  boot()   {"'))
bad += expect("blast: whitespace in the quote is normalised", got, "PASS blast: 4 items checked")
got, _ = check_cited("blast", BLAST.replace('app/Model.php:3 | "protected static function boot() {"', 'app/Model.php:4 | "protected static function boot() {"'))
bad += expect("blast: a quote one line off still matches", got, "PASS blast: 4 items checked")
got, _ = check_cited("blast", BLAST.replace("SCOPE BR2: tenant | app/Model.php:3", "SCOPE BR2: tenant | app/Model.php:6").replace("protected static function boot() {", "}"))
bad += expect("blast: the file's last line is in range", got, "PASS blast: 4 items checked")

got, _ = check_cited("blast", BLAST.replace('app/Model.php:3 | "protected static function boot() {"', 'app/Model.php:1 | "protected static function boot() {"'))
bad += expect("blast: a quote two lines away is not on the cited line", got,
              "FAIL blast: 4 items checked\n  BR2 quote not on app/Model.php:1")
got, _ = check_cited("blast", BLAST.replace('"$r->touch();"', '"$r->delete();"'))
bad += expect("blast: a quote that is not in the file", got,
              "FAIL blast: 4 items checked\n  BR3 quote not on app/Model.php:4")
got, _ = check_cited("current", CURRENT_TXT.replace('"$r->touch();"', '"$r->delete();"'))
bad += expect("current: a quote that is not in the file", got,
              "FAIL current: 2 items checked\n  CS2 quote not on app/Model.php:4")

got, _ = check_cited("blast", BLAST.replace('WRITER BR3: app/Model.php:4 | "$r->touch();"', 'WRITER BR3: app/Model.php:99 | "$r->touch();"'))
bad += expect("blast: a line past the end of the file", got,
              "FAIL blast: 4 items checked\n  BR3 line 99 out of range in app/Model.php")
got, _ = check_cited("blast", BLAST.replace('WRITER BR3: app/Model.php:4 | "$r->touch();"', 'WRITER BR3: app/Model.php:0 | "$r->touch();"'))
bad += expect("blast: line 0 is out of range", got,
              "FAIL blast: 4 items checked\n  BR3 line 0 out of range in app/Model.php")
got, _ = check_cited("current", CURRENT_TXT.replace("app/Model.php:4 | \"$r->touch", "app/Model.php:8 | \"$r->touch"))
bad += expect("current: a line past the end of the file", got,
              "FAIL current: 2 items checked\n  CS2 line 8 out of range in app/Model.php")

got, roots = check_cited("blast", BLAST.replace("WRITER BR3: app/Model.php:4", "WRITER BR3: app/Gone.php:4"))
bad += expect("blast: a cited file that is in no root", got,
              f"FAIL blast: 4 items checked\n  BR3 file not found in {roots}: app/Gone.php")
got, roots = check_cited("current", CURRENT_TXT.replace("CS1: 1 | app/Model.php", "CS1: 1 | app/Gone.php"))
bad += expect("current: a cited file that is in no root", got,
              f"FAIL current: 2 items checked\n  CS1 file not found in {roots}: app/Gone.php")
got, roots = check_cited("blast", BLAST.replace("WRITER BR3: app/Model.php:4", "WRITER BR3: app:4"))
bad += expect("blast: a directory is not a cited file", got,
              f"FAIL blast: 4 items checked\n  BR3 file not found in {roots}: app")

got, _ = check_cited("blast", BLAST.replace('WRITER BR3: app/Model.php:4 | "$r->touch();"', 'WRITER BR3: app/Model.php:4'))
bad += expect("blast: no quoted line", got, "FAIL blast: 4 items checked\n  BR3 needs file:line and a quoted line")
got, _ = check_cited("blast", BLAST.replace('WRITER BR3: app/Model.php:4 | "$r->touch();"', 'WRITER BR3: "$r->touch();"'))
bad += expect("blast: no file:line", got, "FAIL blast: 4 items checked\n  BR3 needs file:line and a quoted line")
got, _ = check_cited("blast", BLAST.replace('WRITER BR3: app/Model.php:4 | "$r->touch();"', 'WRITER BR3: app/Model.php | "$r->touch();"'))
bad += expect("blast: a path with no line number", got, "FAIL blast: 4 items checked\n  BR3 needs file:line and a quoted line")
got, _ = check_cited("current", CURRENT_TXT.replace('| "$r->touch();" |', '|'))
bad += expect("current: no quoted line", got, "FAIL current: 2 items checked\n  CS2 needs file:line and a quoted line")
got, _ = check_cited("current", CURRENT_TXT.replace("CS2: 2 | app/Model.php:4", "CS2: 2 | the model"))
bad += expect("current: no file:line", got, "FAIL current: 2 items checked\n  CS2 needs file:line and a quoted line")

got, roots = check_cited("blast", BLAST.replace("CHAIN: Model | app/Model.php", "CHAIN: Model | vendor/Model.php"))
bad += expect("blast: a CHAIN file that is in no root", got,
              f"FAIL blast: 4 items checked\n  chain file not found in {roots}: vendor/Model.php")
got, roots = check_cited("blast", BLAST.replace("ENTITY: Report | app/Model.php", "ENTITY: Report | app/Report.php"))
bad += expect("blast: an ENTITY file that is in no root", got,
              f"FAIL blast: 4 items checked\n  chain file not found in {roots}: app/Report.php")

got, _ = check_cited("blast", BLAST.replace("READER BR4", "READER BR3"))
bad += expect("blast: a duplicate id", got, "FAIL blast: 4 items checked\n  duplicate ids: ['BR3']")
got, _ = check_cited("current", CURRENT_TXT.replace("STEP CS2", "STEP CS1"))
bad += expect("current: a duplicate id", got, "FAIL current: 2 items checked\n  duplicate ids: ['CS1']")

got, roots = check_cited("blast", BLAST.replace("WRITER BR3: app/Model.php:4", "WRITER BR3: app/Gone.php:4").replace("READER BR4", "READER BR1"))
bad += expect("blast: every failure is reported, duplicates last", got,
              f"FAIL blast: 4 items checked\n  BR3 file not found in {roots}: app/Gone.php\n  duplicate ids: ['BR1']")

d = tmp({"main/app/Model.php": MODEL_PHP, "pkg/src/Job.php": JOB_PHP})
roots = os.path.join(d, "main") + "," + os.path.join(d, "pkg")
path = os.path.join(d, "out.txt")
open(path, "w").write("WRITER BR1: app/Model.php:4 | \"$r->touch();\" | a\nWRITER BR2: src/Job.php:4 | \"->update(['x' => 1]);\" | b\n")
bad += expect("blast: a file may live in any of several roots", run("blast", roots, path), "PASS blast: 2 items checked")
open(path, "w").write("WRITER BR1: src/Job.php:4 | \"$r->touch();\" | a\n")
bad += expect("blast: the quote is read from the root that has the file", run("blast", roots, path),
              "FAIL blast: 1 items checked\n  BR1 quote not on src/Job.php:4")

# ---- merge ----


def slice_dir(name, ids):
    d = tempfile.mkdtemp()
    p = os.path.join(d, name)
    os.makedirs(p)
    for f, text in ids.items():
        open(os.path.join(p, f), "w").write(text)
    return p


S1 = {"map.txt": "BRANCH: app\n  R1: save sends\n  R2: delete sends\n",
      "gaps.txt": "TAG: R1 | update | save sends\nGAP 1: R2 | q | Engineer | n\nGAP 2: U1 | q about R1 | PM | n\n",
      "pm-answers.md": 'ANSWER GAP 1: q | "yes" | 2026-10-13\nPENDING GAP 2: q | asked 2026-10-13\n'}
S2 = {"map.txt": "BRANCH: app\n  R1: other save\n  U1: unsure\n",
      "gaps.txt": "GAP 1: R1 | q | PM | see R1\n",
      "pm-answers.md": 'PENDING GAP 1: q | asked 2026-10-14\nCORRECTION C1: "R1 is instant" | hourly, b.php:3 | posted 2026-10-15 | OPEN\n'}
a, b = slice_dir("alpha", S1), slice_dir("beta", S2)
out = os.path.join(tempfile.mkdtemp(), "merged")
bad += expect("merge writes the combined inputs", run("merge", out, a, b).split("\n")[0], f"PASS merge: 2 slices into {out}")
m = {f: open(os.path.join(out, f)).read() for f in ("map.txt", "gaps.txt", "pm-answers.md", "slices.txt")}
bad += expect("merge renumbers R in slice 2", "  R201: other save" in m["map.txt"] and "  R102: delete sends" in m["map.txt"], True)
bad += expect("merge renumbers GAP and rewrites references in the lines",
              "GAP 201: R201 | q | PM | see R201" in m["gaps.txt"] and "GAP 102: U101 | q about R101 | PM | n" in m["gaps.txt"], True)
bad += expect("merge renumbers answers and corrections",
              'PENDING GAP 201: q' in m["pm-answers.md"] and 'CORRECTION C201: "R201 is instant"' in m["pm-answers.md"]
              and "ANSWER GAP 101:" in m["pm-answers.md"], True)
bad += expect("merge writes slices.txt",
              m["slices.txt"], f"SLICE 1 | alpha | R101-R199 | {a}\nSLICE 2 | beta | R201-R299 | {b}\n")
out2 = os.path.join(tempfile.mkdtemp(), "merged")
run("merge", out2, a, b)
bad += expect("merge is idempotent",
              all(open(os.path.join(out2, f)).read() == m[f].replace(a, a) for f in ("map.txt", "gaps.txt", "pm-answers.md")), True)
big = slice_dir("big", {**S1, "map.txt": "  R100: too many\n"})
bad += expect("merge fails on an id of 100 or more",
              run("merge", os.path.join(tempfile.mkdtemp(), "x"), big).split("\n")[1], "  slice big map.txt has id R100, 100 or above")
nopm = slice_dir("nopm", {"map.txt": "  R1: x\n", "gaps.txt": ""})
bad += expect("merge fails when pm-answers.md is missing",
              run("merge", os.path.join(tempfile.mkdtemp(), "x"), nopm).split("\n")[1],
              "  slice nopm is missing pm-answers.md. Write it from templates/pm-answers.md")

# ---- exit codes: a caller can trust the exit code, not just the first word ----

SHARED = os.path.join(HERE, "..", "..", "shared")


def exit_code(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True).returncode


roots, good = repo_case(BLAST)
_, wrong = repo_case(BLAST.replace("app/Model.php:4 |", "app/Model.php:1 |"))
edd = os.path.join(HERE, "check_edd.py")
blast = os.path.join(SHARED, "check_blast.py")
bad += expect("check_edd exits 0 on PASS", exit_code(edd, "blast", roots, good), 0)
bad += expect("check_edd exits 1 on FAIL", exit_code(edd, "blast", roots, wrong), 1)
bad += expect("check_blast exits 0 on PASS", exit_code(blast, roots, good), 0)
bad += expect("check_blast exits 1 on FAIL", exit_code(blast, roots, wrong), 1)
prose = tmp({"ok.md": "The script checks the file.\n", "bad.md": "The script serves as the guard.\n"})
bad += expect("writing exits 0 on PASS", exit_code(edd, "writing", os.path.join(prose, "ok.md")), 0)
bad += expect("writing exits 1 on FAIL", exit_code(edd, "writing", os.path.join(prose, "bad.md")), 1)

sys.exit(1 if bad else 0)
