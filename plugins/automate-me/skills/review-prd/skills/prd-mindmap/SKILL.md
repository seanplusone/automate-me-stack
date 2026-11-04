---
name: prd-mindmap
description: Break a PRD into a mind map of goal, branches and points. Use as step 1 of a PRD review, or when asked to map a PRD.
---

# PRD mind map

Turn one PRD into a fixed-format outline. Only describe what the PRD says. Do not judge, add or fix anything.

## Step 1. Find the goal

Quote the PRD's goal line. If there is none, write `GOAL: not stated`.

Check. The goal is a word-for-word quote or `not stated`.

## Step 2. Split into points

A point is one thing the PRD says the system should do. Number them R1, R2, and so on, in PRD order. Copy each line word for word.

- Background goes in `CONTEXT`.
- Out-of-scope lines go in `OUT OF SCOPE`.
- Lines where the PM is unsure about how the system behaves go in `PM UNSURE`, numbered U1, U2.
- Lines about schedule, people or business context go in `CONTEXT`, even if they sit under an "unsure" heading. Classify by what the line says, not by its heading.
- PMs often answer review questions in a questions-and-answers section at the end, instead of editing the line the question was about. Each question there goes in `CONTEXT`. Each answer is a point, even when it repeats a line above it, because the PM may change the answer without changing that line.

Check. Every PRD sentence lands in exactly one of: a point, context, out of scope, PM unsure.

Why. A sentence nobody placed is where gaps hide.

## Step 3. Name the branches

- One branch per system the PRD names as a place data lives. Use the PRD's own name for it.
- One `Between` branch, for moving data from one system to another.
- One `Result` branch, for rules about the end state.

Check. Every system branch name appears in the PRD.

## Step 4. Place each point

Apply these in order. The first match wins.

1. It states an end state that must hold ("always match", "must be in sync"): `Result`.
2. It moves or limits moving data between systems: `Between`.
3. It acts inside one system: that system's branch.

Place each U item under the branch its topic belongs to. If none fits, list it under `UNPLACED`.

Check. Every R sits under exactly one branch. Nothing is placed by guess. Anything unclear goes to `UNPLACED`.

Why. A fixed order gives the same map every run.

## Output format

Use this format exactly. A script reads it.

```
GOAL: <quote>

BRANCH: <system name>
  R<n>: <quote>
  U<n>: <quote>

BRANCH: Between
  R<n>: <quote>

BRANCH: Result
  R<n>: <quote>

UNPLACED:
  U<n>: <quote>

CONTEXT:
  <quote>

OUT OF SCOPE:
  <quote>

COUNTS: points <n>, branches <n>, unsure <n>, unplaced <n>
```

## Hard requirements

- The run fails if any quote is not word for word in the PRD.
- The run fails if any point sits under zero or two branches.
- If the PRD is missing or has no points, stop and say so.

## Limits

- No questions, gaps or opinions. That is a later step.
- Do not read the codebase.
