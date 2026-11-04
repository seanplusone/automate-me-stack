# Playbook: Write an EDD

Input is a reviewed PRD and the project repo. Output is a draft EDD a person approves before any code. Copy these steps into the todolist word for word. A skipped step stays as `skip: <reason>`.

## Steps

1. **Check inputs.** The PRD map is approved. Each PM question has a line in `pm-answers.md` (format in `templates/pm-answers.md`), answered or PENDING. A PENDING answer or an OPEN correction does not stop the run. Each probe or spike follows `templates/evidence.md`. The layout is `<input dir>/layout.json` when it exists, else `rules/edd-sections.json`. Read `<input dir>/project.md` when it exists (`templates/project.md`). With several PRD slices, run `python3 "$SKILL_DIR"/check/check_edd.py merge <out dir> <slice dir>...` first, and use `<out dir>` as the input dir. Stop if the map is missing.
2. **Check the docs agents read.** Run `check_edd.py names` on the project docs the agents will load. List every name that does not exist in the search roots. Do not fix them here. Report them.
3. **Current state.** Run `../shared/skills/current-state` steps 1 to 3, with each system branch and the Between branch of the map as one flow, named as in the map. Run `check_edd.py current` and fix until it passes. Then run its step 4. Append the current-state entry to `out/walkthrough.md` (`templates/walkthrough.md`).
   - PM questions. If the trace shows existing behavior a customer would notice, and the PRD does not say whether it should change, add `PM QUESTION: <plain question> | CS<n>` to the trace. For example, "Today the other system overwrites app edits on every sync. Should that change?" Write one question each, following W13 to W16 in `../shared/writing-rules.md`. Do not design around it. End COUNTS with `pm questions <n>`. PM QUESTION lines go to the person, to send with the next PM round.
4. **Blast radius.** Run `../shared/skills/blast-radius` steps 0 to 5 once per entity the traced steps write. Run `check_edd.py blast` and fix until it passes. Then run its step 6. Append the blast-radius entry to `out/walkthrough.md`.
5. **Evidence.** List the probes and spikes that exist, including any from `spike-before-edd.md`. Run `check_edd.py evidence <dir>`. Any input marked "verify" with no evidence stays unverified.
6. **Design options.** Run `../shared/skills/design-options` in PROPOSE mode. What the change must do is the approved map, the PM answers and the gap list. The current state is the CS and BR ids. Write the lines to `arch.txt` in the run dir. Each ARCH SERVES at least one R, GAP or ANSWER id, and `check_edd.py delta` checks it in step 7. A choice no evidence settles becomes a Decision in the EDD with its options listed, and its sketch becomes a spike in step 8. A person approves the ARCH lines before step 7. This is where precedents and house standards decide the shape. Append the design-options entry to `out/walkthrough.md`.
7. **Delta list.** Run step 1 of `skills/edd-draft`. A change that rests on an unanswered question carries `ASSUMES`. A change follows the code, not a PRD statement a CORRECTION says is wrong. Run `check_edd.py delta` and fix until it passes.
8. **Spikes.** Run `skills/spikes`. Each spike the design depends on runs, following the steps in `skills/spikes`. If it could run but has not, write it as PLANNED. If something outside the team stops it, give a BLOCKED reason. A spike answer that contradicts a DELTA or ARCH stops the run.
9. **Draft.** Run the rest of `skills/edd-draft`, diagrams included. Then run `sh "$SKILL_DIR"/check/check_all.sh <input dir> <run dir> <repo>`. It uses the layout from step 1. It runs `delta`, `sections`, `coverage`, `hazards`, `spikes`, `diagrams`, `names` and `writing`, and renders the diagrams when `mmdc` is installed. Rewrite only the flagged lines.
10. **Panel check.** Run `../shared/skills/panel-check` on the EDD, the delta list and the inputs, with these lenses:
   - Premise: what must be true for this design to work at all? Attack it against the real code.
   - Correctness: each hazard's evidence supports it, and each mitigation is concrete. Read the code, not the BR or CS descriptions.
   - Scope: each DELTA actually serves its BECAUSE id. Each ENABLE is really needed. Nothing NOTICED crept into the design.
   - Standards: each ARCH follows the project's rules files and its precedent.
   It also writes `CONTRADICTS | <EDD statement> | <GAP n>` for anything against a PM answer. A finding that survives the panel stops the run and goes to the person. Append the panel entry to `out/walkthrough.md`. If `project.md` names a design review command, the person runs it on the draft. write-edd never runs project commands. State the command in the report.
11. **Draft out.** Save the EDD with Status "Draft". Never mark it approved. A person approves it, and only then can implementation start. If `project.md` names where an EDD lands, write the EDD to that file name in the run dir. Put the exact path, branch and PR line in the report's Hand-off line. write-edd does not create the branch or the PR.

## Stop rules

- Map missing or not approved: stop at step 1.
- Current state or blast radius fails its check: stop at that step.
- ARCH lines not approved: stop at step 6.
- A spike answer contradicts a DELTA or ARCH: stop at step 8.
- A finding survives the panel: stop at step 10.

## Reply

Write the plain-language report from the root `SKILL.md`.

## After the EDD is reviewed

Run `../shared/playbooks/learn-from-run.md`.
