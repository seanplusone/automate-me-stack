# write-edd

Part of `automate-me`. Writes a draft EDD from a reviewed PRD, with blast radius and evidence. A person approves the EDD before any code.

Status: working. Scored runs on the invented practice case. Drafts while the PRD is still moving: PENDING answers, PRD corrections, several PRD slices in one EDD, and the team's own layout. No run on a real PRD yet.

## Layout

```
write-edd/
  SKILL.md                     orchestrator: runs the playbook, reports back
  playbooks/
    write-an-edd.md            the steps, start to finish
  skills/
    edd-draft/SKILL.md         delta list, then the EDD in the house layout
  rules/
    edd-sections.json          the built-in layout, tables, roles and evidence patterns
  templates/
    pm-answers.md              how PM answers and PRD corrections are recorded
    evidence.md                how a probe or spike is recorded (RAN, BLOCKED, PLANNED)
    project.md                 optional project file: design-doc skill, layout, review command, hand-off names
    walkthrough.md             how out/walkthrough.md explains findings, and what each part of an EDD is for
  check/
    check_edd.py               current, blast, delta, sections, coverage, hazards, spikes, diagrams, names, writing, merge
  cases/
    order-sync/           invented practice repo, inputs, key, scored runs
                          (run-3 is the passing run; run-1 and run-2 are earlier stopped runs kept for history and fail check_all.sh)
```

Playbook step 3 runs `../shared/skills/current-state/SKILL.md` (how each branch works today) and adds the PM questions.

Playbook step 6 runs `../shared/skills/design-options/SKILL.md` (the system shape) in PROPOSE mode and adds the PRD ids and the approval.

Also shared with other skills, in `../shared/skills/`: `blast-radius/SKILL.md` (what fires, filters or depends on an entity) with `blast-radius-reference.md` beside it (copy into the project as `.claude/blast-radius.md`), and `panel-check/SKILL.md`.

## Inputs from review-prd

- `map.txt` (approved)
- `gaps.txt` (the Engineer gaps become design work)
- `pm-answers.md`, answered or PENDING, plus CORRECTION lines (below)
- `layout.json`, optional. Replaces the built-in layout for this run.
- `project.md`, optional. Format in `templates/project.md`.

PENDING answers and OPEN corrections do not stop a run. A change that rests on a PENDING question carries `| ASSUMES GAP <n>`, and the decisions row for that question lists it. A change that rests on a spike that is PLANNED or BLOCKED carries `| ASSUMES SPIKE<n>`.

A correction is a line engineering adds when a PRD statement is wrong about how the product works today:

```
CORRECTION C<n>: <the PRD statement, quoted> | <what the code does, with file:line> | posted <date> | OPEN|ACCEPTED|REJECTED
```

The EDD follows the code. The section named by the `prd_record` role lists every C id, and says what the design assumes for OPEN and REJECTED ones.

## Several PRD slices in one EDD

`python3 check/check_edd.py merge <out dir> <slice dir>...` reads `map.txt`, `gaps.txt` and `pm-answers.md` from each slice dir (the slice name is the dir name, or its parent's when the dir is `out`). It writes the three files to `<out dir>`, with slice k's ids moved to k*100+n (R, U, GAP and C), every reference rewritten, and a `slices.txt` with one line per slice:

```
SLICE <k> | <name> | R<k>01-R<k>99 | <source dir>
```

It fails if a source id is 100 or above or a file is missing. Run it again with the same inputs and the output is the same. Use `<out dir>` as the input dir.

## Layout

The layout is `<input dir>/layout.json` when it exists, else `rules/edd-sections.json`. A layout names `header`, `sections` and `tables`. It may leave out `evidence_patterns`, `min_level`, `level_needs_run` and `diagrams`, which then come from the built-in file. Set `diagrams.section` to the section that holds the diagrams.

`tables` is keyed by section name. A value is one column list, or a list of column lists when a section holds several tables. Each list must match the header of some table in that section, wherever it sits.

`roles` is optional. It names the section for each role write-edd needs:

```
"roles": {"hazards": "Known hazards", "decisions": "Decisions blocking build start", "prd_record": "Summary"}
```

Those are the defaults. The hazards check finds its table in the `hazards` section by its Evidence and Level columns. The decisions check reads any table row in the `decisions` section, so it needs no column names. Two roles can name one section.

## Checks

Each check prints PASS or FAIL and exits 1 on FAIL.

| Command | Fails when |
| --- | --- |
| `current <repo> <current.txt>` | A traced step's file:line does not exist, or the quote is not on that line |
| `blast <repo> <blast.txt>` | A file:line does not exist, or the quote is not on that line |
| `delta <delta> <map> <gaps> <answers> <arch> <current> [evidence...]` | A DELTA has no real BECAUSE or CURRENT. A change is not under a real ARCH. An ENABLE has no evidence. An ARCH has no change under it. An ASSUMES names an answered GAP, a spike that ran, or an unknown id. A CORRECTION has no file:line, date or status |
| `sections <edd> <layout>` | A header, section or table column is missing or out of order. A column list must match some table in its section |
| `coverage <edd> <map> <gaps> <answers> <layout> <id files...>` | An R, Engineer GAP, BR, ARCH, DELTA or ENABLE id is never cited. A C id is missing from the `prd_record` section, or an OPEN or REJECTED one does not say what the design assumes. A PENDING GAP or PLANNED spike has no decisions row, the row omits a D id that ASSUMES it, or a spike row does not say "spike". Pass the evidence files among the id files |
| `hazards <edd> <layout>` | A hazard has no file:line, BR, CS, PROBE or SPIKE as evidence, no level, level 1, or claims level 4 or 5 without a PROBE or SPIKE |
| `spikes <edd> <evidence dir> <layout>` | A cited spike has no file. A RAN file has no result, a LEVEL outside 2 to 5, or names production without `RUNNER: person` and read-only. A PLANNED spike has a result or no method. A level 4 or 5 hazard cites no PROBE or SPIKE that ran at that level or higher |
| `evidence <evidence dir>` | The same per-file rules as `spikes`, on every PROBE and SPIKE file in a dir, with no EDD |
| `diagrams <edd> <delta> <layout>` | A diagram kind is missing, a delta id is not drawn, or a drawn id is not in the delta list |
| `merge <out dir> <slice dir>...` | A slice file is missing, a source id is 100 or above, or two slices share a name |
| `names <repo> <files...>` | A doc names a class, method or command that is not in the repo, unless marked `(new)` |
| `writing <file>` | A shared writing rule marked `[script]` is broken |

`blast` and `names` take a comma-separated list of repos. "Not found" means not in those repos. If `vendor/` or a sibling app is not checked out, real code can show as missing. Read each miss by hand before calling it wrong.

`current` and `blast` run `../shared/check_blast.py`, the same check the shared current-state and blast-radius skills name.

## Project facts stay in the project

Where a framework hides hooks, or which docs are wrong, belongs in the project repo, for example `.claude/blast-radius.md`. Nothing company-specific goes in this folder.
