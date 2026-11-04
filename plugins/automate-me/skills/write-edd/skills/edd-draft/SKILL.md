---
name: edd-draft
description: Write the delta list and the EDD from an approved map, PM answers, current state, blast radius and approved ARCH lines. Use as the drafting step of write-edd.
---

# EDD draft

Turn checked inputs into a delta list, then an EDD in the house layout. Every claim traces to an input. Nothing is invented.

## Inputs

- The approved PRD map (R and U numbers).
- `pm-answers.md`: one ANSWER or PENDING line per PM question (format in `templates/pm-answers.md`).
- The "For the design doc" gap list (GAP numbers).
- Current state (CS ids), blast radius (BR ids), approved ARCH lines (A ids).
- `pm-answers.md` also holds CORRECTION lines: engineering's notes that a PRD statement is wrong about today's product.
- Evidence files: probes and spikes (format in `templates/evidence.md`), including `out/evidence/` from the spike step.
- The layout: `<input dir>/layout.json` when it exists, else `rules/edd-sections.json`. Its `roles` object names the section for each role. `hazards` is the hazards section, `decisions` is the decisions section, `prd_record` is where corrections are listed. Where this skill says "the hazards section" it means the one the layout names.
- `<input dir>/project.md` when it exists (format in `templates/project.md`).

## Step 1. Write the delta list

Write `out/delta.txt`. Every change the feature needs is one line.

```
DELTA D<n>: <branch> | CURRENT <CS id or NONE> | CHANGE <what changes> | BECAUSE <R n, GAP n or ANSWER GAP n> | ASSUMES <GAP n or SPIKE n> | UNDER <A id>
ENABLE E<n>: <change the feature needs that the PRD does not mention> | ENABLES <R n> | NEEDED BECAUSE <BR, CS, PROBE or SPIKE id> | UNDER <A id>
NOTICED N<n>: <file:line> | <what was found>
```

- **DELTA.** A change with a PRD reason. CURRENT names the traced step it changes, or NONE for something new.
- **ASSUMES.** Optional. Add it when the change rests on a question with no answer: a PENDING GAP, or a spike that is PLANNED or BLOCKED. Name that one id. Drop it when the question is answered or the spike ran. The check fails on an ANSWERed GAP or an unknown id. Count these as provisional deltas in the report.
- **Corrections.** A change follows what the code does today (the CS lines), not a PRD statement that a CORRECTION says is wrong.
- **ENABLE.** A supporting change, such as fixing a lock the feature depends on. It must name the requirement it unblocks and the evidence that it is needed.
- **NOTICED.** Anything found with no PRD reason: a bug, a cleanup, another writer of the same data. One line. Never designed.

Check. `check_edd.py delta` passes.

Why. A change with no PRD reason is a tangent. The gate keeps it out of the design, and NOTICED keeps it from being lost.

## Step 2. Lay out the sections

Write the header and every section from the layout, in order. A section with nothing to say gets one line saying why.

When `project.md` sets `design_doc_skill`, load that SKILL.md and every checklist, voice and template file it points to. Draft by following them. Feed in the CS, BR, ARCH, DELTA and ENABLE ids, the PM answers, the corrections and the spikes. The layout file still gates the result, so the sections and tables must match it. When it is unset, use the steps below.

## Step 3. Fill the sections from the deltas

- The architecture section (the one `diagrams.section` names): one part per ARCH line. Say what it reuses or mirrors, with the precedent. Cite it as `[A1]`.
- The sections that describe the change (data model, backend and frontend in the built-in layout): one entry per DELTA and ENABLE, cited as `[D3]` or `[E1]`, with its BECAUSE id.
- Each R point is cited at least once, as `[R3]`, either through a delta or a Decision.
- Each Engineer gap is answered by a delta, or becomes a Decision. Cite it as `[GAP 2]`.
- Each PENDING line becomes a row in the decisions section. The default is engineering's position. The row cites `[GAP n]` and lists every D or E id that ASSUMES it. The owner is the PM, unless the input names someone else. An answer that does not settle the question stays PENDING.
- Each planned spike becomes a row in the decisions section too. The row says it is a spike, cites the SPIKE id and lists every D or E id that ASSUMES it. A PENDING GAP the spike stands in for is cited in the same row.
- Each CORRECTION is listed by its C id in the `prd_record` section, with the PRD statement, what the code does, and its status. For OPEN and REJECTED, say what the design assumes.
- Each BR is a Known hazard, or named as unchanged. Cite it as `[BR4]`.
- NOTICED lines do not go in the EDD.

Check. `check_edd.py coverage` passes.

## Step 3b. Diagrams

Draw two mermaid diagrams in the section `diagrams.section` names, built only from the delta list. Label each arrow or step with the D or E id it comes from.

- **Data flow.** A `flowchart LR`. Boxes are the systems and stores the deltas touch. Arrows are the data that moves, labeled like `-->|D1 status, notes|`.
- **Sequence.** A `sequenceDiagram` of the main path, from the user's action to the result. Declare every `participant` first. Failure paths go in `alt` blocks.

Every DELTA and ENABLE id appears in at least one diagram. A diagram shows nothing that is not in the delta list. Existing parts with no change are drawn plainly, with no id.

Check. `check_edd.py diagrams` passes.

## Step 4. Known hazards

In the hazards section the layout names, one row per hazard: what can go wrong, its evidence, how sure we are, and the mitigation.

- Evidence is a `file:line`, a BR, a CS, a PROBE or a SPIKE. Nothing else counts.
- Level is how sure we are, from `templates/evidence.md`. 2 is a cited line. 3 is a walked-through failure. 4 is a probe or spike that ran. 5 is reproduced in the running app. Level 1, "said so", is not allowed.
- The fact the whole design depends on should reach level 4. If its spike is planned or blocked, say so under the table, with the SPIKE id and its reason.

Check. `check_edd.py hazards` passes.

## Step 5. Decisions

In the decisions section the layout names, one row per open decision: options, owner and a default if unblocked today. Use the columns of the layout's table. Where it has no column for one of these, say it in the row's text.

- For a decision with no precedent, list 2 or 3 options from the ARCH step. Say what evidence would settle it.
- Write the default as "Do X. If Y, do Z."

## Step 6. Name only real code

Any existing class or method you name in backticks must exist in the repo. Mark anything new with `(new)`, as in `` `WriteClient` (new) ``.

Check. `check_edd.py names` passes.

## Limits

- Load `../../../shared/writing-rules.md` before writing.
- Do not change the PRD, the PM answers or the ARCH lines.
- Status stays "Draft". Only a person approves an EDD.
