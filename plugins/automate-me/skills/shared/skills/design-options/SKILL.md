---
name: design-options
description: Decide the shape of a change, or judge the shape someone else chose. For each capability, configure or reuse what exists, or compare two designs when nothing does. Use before designing a change, such as an EDD or a fix, or when reviewing whether a change has the right shape.
---

# Design options

Input is what a change must do, or a change someone else wrote, and the repo. Output is a fixed-format list, one ARCH line per capability. Pick the shape. Write no code.

Adapted from Phases A and B of pstack's `architect` skill (MIT, Lauren Tan). The ideas taken are grounding first, designing twice, a red-flag screen and preferring the smaller interface. Unlike `architect`, this stops before implementation. If pstack is installed, `/architect` with a checkpoint can supply candidate shapes. Rewrite them as OPTION lines. `architect` reads no standards and searches for no precedent, so steps 2 and 3 still run.

## Modes

The caller names one.

- **PROPOSE.** You design a change, such as an EDD or a fix. The ARCH lines are the shape to build.
- **JUDGE.** You review a change someone else wrote. Take the capabilities from what the diff adds, and run the steps as if you were designing it. The change's own shape is option 1 in step 4. Then write one SHAPE line per ARCH.

## Input

- PROPOSE: what the change must do, with the caller's ids if it has them. The current-state trace and blast radius, if the caller ran them.
- JUDGE: the diff, and what its author says it does.
- The project reference, `.claude/blast-radius.md` in the project repo. This skill reads its Standards and Capability index sections. The template is `../blast-radius/blast-radius-reference.md`.

## Step 1. Name what is really new

List what the change needs that does not exist today, or must change. Name each by what it does, not by a class name. For example, "store and refresh access tokens for each customer", not "TokenManager".

Strip each need to the smallest new behavior. Anything more either exists already, and step 3 finds it, or is not needed. In JUDGE, what the change builds beyond that is a FAILS.

## Step 2. Read the standards and the siblings

Read the project's rules files before designing. If a rule already says how to do this kind of thing, that rule decides. Cite it.

Then read two or three siblings, existing pieces of the same kind. The new piece takes their shape: file layout, names, section order, output format and interface. A reader who knows one sibling reads the new one without surprise.

## Step 3. Search for a precedent

Search the code for something that already does this capability, by what it does.

- Check the capability index first.
- Then search by behavior terms, such as words the code would use for that job. Record every search.
- A precedent is existing code that solves the same kind of problem. Cite its file and line.

First ask whether the need is a configured instance of an existing kind: the same thing with different settings. If it is, configure or extend that kind, as `USE reuse`. Never add a second kind beside it.

Otherwise, if a precedent exists, reuse it or mirror it. Departing from it needs a written reason.

If none exists, write `PRECEDENT NONE`. Only then go to step 4.

Why. A new pattern next to an existing one means two ways to do one task. The next person copies whichever they find first.

## Step 4. Design twice, when there is no precedent

Write at least two structurally different options. Not two flavors of the same shape.

Screen each against these red flags:
- **Shallow module.** Callers must coordinate several calls for one job.
- **Information leakage.** The same internal decision appears in more than one place.
- **Split ownership.** More than one place writes the same state.
- **Two ways to do one task.** The design adds a second way to do something that already has one.
- **Hand-synced list.** Two lists must be edited together.

Prefer the option with the smaller, simpler public interface that hides more behind it.

When two options stay close, or people disagree, settle it with a small runnable sketch on the real runtime, not by argument. pstack's Prototype playbook runs one when it is installed. If no sketch can run yet, name the sketch that would settle it and leave the choice open for the caller. Do not pick by taste.

## Step 5. Place each piece

Check every ARCH, reuse included, and every option:

- **Shallowest layer.** Each fact lives in the one place that must know it. A layer that would behave the same without knowing about the change does not change.
- **Invariants in the base.** A rule that must hold for every user of a shared piece goes in that piece, not in each caller.

Example. A form needed a "Priority" field with three fixed choices. The first design added a new kind of field, with its own runtime element, renderer and builder code. It was a select field with three settings filled in (step 3). The fix was a preset in the form builder that fills in an ordinary select, so the runtime never learns presets exist. The base field class keeps presets out of repeating groups, so no caller has to remember that rule (step 5).

## Output format

Use this format exactly. A calling skill may add its own line types, but no added line starts with `ARCH`, `OPTION` or `SHAPE`.

```
ARCH A<n>: <capability> | SERVES <the caller's ids> | PRECEDENT <file:line or NONE> | STANDARD <rule file or NONE> | USE reuse, mirror or new | WHY <one sentence>
OPTION A<n>.<k>: <shape> | RED FLAGS <none or list> | INTERFACE <what callers see>
SHAPE A<n>: HOLDS or FAILS | <for FAILS, the step it fails and the shape the steps pick> | <file:line>
SEARCHES: <every search run, one per line>
```

- Leave out `SERVES` when the caller has no ids.
- Write OPTION lines only for ARCH lines with `USE new`.
- Write SHAPE lines only in JUDGE. A FAILS from step 3 or step 5 means the change needs a different shape, not a fix in place.

## Hard requirements

- Every PRECEDENT and SHAPE cites a real file and line.
- Read only in the repo. A sketch from step 4 runs in a scratch folder and is thrown away.
- No code.
