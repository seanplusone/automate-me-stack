---
name: current-state
description: Trace how a flow works today, from its trigger to its effect, with file and line for every step. Use before designing, fixing or reviewing a change to existing code.
---

# Current state

Input is one or more flows and the repo. Output is a fixed-format list a script can check. Reverse engineer what exists today. Do not design or judge. Only trace and cite.

Adapted from pstack's `how` skill (MIT, Lauren Tan). The ideas taken are a trace from trigger to effect with real code for every step, and for a wide trace, explorers split by angle. Each explorer also reports boundaries and non-obvious behavior. Unlike `how`, the output is checked lines, not an explanation.

## Input

- The flows to trace. A flow is a job the code does today, such as a feature area, the path behind a bug, or a PR's entry point. The caller names each one.
- The repo. Read the search roots from the project reference, as `../blast-radius/SKILL.md` step 0 lists them.

## Step 1. One trace per flow

For each flow, find the existing code that does that job today.

- Start from the trigger: a user action, a schedule, a webhook, a command.
- Follow each call to the effect: a write, a send, a response.
- Write each hop as one STEP line, in order.

If a flow has no existing code, write `NONE` with the searches you ran. Do not invent a flow.

Check. Every STEP has a real file and line, and the quoted code is on that line.

Why. Anything built on a guessed flow is wrong in ways no reviewer can see.

## Step 2. Split a wide flow (optional)

Use this when one flow spans many files or services. Split it into 2 to 4 angles, each a distinct slice, such as entry points, storage, background jobs or outbound calls. Start one explorer per angle, all at once, with file paths, not pasted text. Each explorer returns:

- STEP lines in the output format below, for its slice only.
- Boundaries: where its slice takes input from, or hands output to, other code.
- Non-obvious: anything that works differently from how it looks.

Merge the STEP lines into one trace per flow, in order, and renumber the CS ids. Every boundary ends in a STEP or a NONE. Every non-obvious item is stated in the description of the STEP it is about. The two notes do not go in the output.

## Step 3. Describe from the body

Each STEP's "what happens" comes from reading the code at that line, not from the name of the method.

Why. A real file and line with a wrong description passes the script check, and whatever is built on it inherits the wrong meaning.

## Step 4. Verify with a different model

Run this after the script check passes. A different model reads the code behind every CS line and writes one line for each description that is wrong:

```
WRONG CS | <id> | <what the code really does>
```

Fix every WRONG CS before anyone builds on the trace. If only one model family is available, follow `../panel-check/SKILL.md` step 1.

## Output format

Use this format exactly. One BRANCH line opens each flow. A calling skill may add its own line types and counts, but no added line starts with `STEP`.

```
ROOTS: <path>, <path>
BRANCH: <flow name, as the caller gives it>
STEP CS<n>: <order in this flow> | <file>:<line> | "<code on that line>" | <what happens>
NONE: <flow> | <searches run>
SEARCHES: <every search run, one per line>
COUNTS: branches <n>, steps <n>, none <n>
```

## Hard requirements

- The run fails if any `file:line` does not exist, or the quote is not on that line. Check it with `python3 "$SKILL_DIR"/../../check_blast.py <roots> <file>`. `$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.
- CS numbers are unique across all flows. Callers cite them.
- Read only. Never run the app, its tests or its commands.
- Nothing here is a design decision.
