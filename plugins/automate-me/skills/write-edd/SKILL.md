---
name: write-edd
description: Write a draft EDD from a reviewed PRD. Traces today's code, checks blast radius, picks the design shape from precedents and house standards, and gates every change on a PRD reason. Use after review-prd, when asked to write or draft an EDD.
---

# EDD mode

The orchestrator. It runs the playbook, calls the sub-skills, and reports back. It does no analysis itself.

## Run

1. Open `playbooks/write-an-edd.md`. Copy its steps into the todolist word for word.
2. Follow the steps. Each one names the sub-skill or script it uses.
3. Report back in the format below.

While PM answers are still coming, run `playbooks/spike-before-edd.md` first. Its evidence dir is this playbook's evidence input.

## Sub-skills

- `skills/edd-draft`: the delta list, then the EDD in the run's layout (or by the project's design-doc skill), with a data-flow and a sequence diagram.
- `skills/spikes`: runs each spike the design depends on, or records why it is blocked.
- `../shared/skills/current-state`: how each branch works today, step by step. The playbook adds the PM questions.
- `../shared/skills/blast-radius`: what fires, filters or depends on each entity.
- `../shared/skills/design-options`: the system shape, from precedents, standards, or two compared designs. The playbook adds the PRD ids and the approval.
- `../shared/skills/panel-check`: several reviewers with different lenses.

## Report back

Load `../shared/writing-rules.md` before writing. Write `out/report.md`:

```
# EDD: <feature name>

**What the design does.** <2 to 4 sentences, in user terms.>

**How it is built.** <One line per ARCH: what it reuses or mirrors, or why it is new.>

**Biggest hazards.** <One line each, with its evidence id and level.>

**Decisions you need to make.** <One line each, with owner. Say which deltas rest on each unanswered question or planned spike.>

**PRD corrections.** <One line per CORRECTION: C id, status, and what the design assumes. Or "None.">

**New questions for the PM.** <PM QUESTION lines from the current-state step, numbered, or "None.">

**Noticed, not designed.** <NOTICED lines: bugs and side findings, one each, or "None.">

**Docs that name missing code.** <From step 2, or "None.">

**Not verified.** <Claims with no probe or spike yet, and each PLANNED or BLOCKED spike with its reason.>

**Stopped or blocked.** <Why, or "None.">

**Walkthrough.** Each step's findings explained for you: `out/walkthrough.md`.

**Hand-off.** <From project.md: the design review command to run, and the EDD's exact path, branch and PR line. Or "None named.">

**Changed.** Nothing. The EDD is a draft at <path>. Status is Draft until you approve it.

Counts: R covered <n>/<n>, GAP covered <n>/<n>, CS steps <n>, BR <n>, ARCH <n>, DELTA <n>, ENABLE <n>, NOTICED <n>, hazards <n>, decisions <n>, spikes ran <n>, spikes planned <n>, spikes blocked <n>, unverified <n>, provisional deltas <n>, corrections <n> (open <n>).
```

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. Run `python3 "$SKILL_DIR"/check/check_edd.py writing out/report.md`. Rewrite only flagged lines. Run it on `out/walkthrough.md` too.

## Guards

- Read only in the project repo. Never run its app, tests or commands. Spikes run in a scratch folder against a sandbox named in `sandbox.md`, never production.
- Never mark an EDD approved. Never start implementation. Never run a command a `project.md` names. State it in the report.
- Project facts, such as where a framework hides hooks, live in the project repo, not here.
- Sub-agents get file paths, not pasted text.
