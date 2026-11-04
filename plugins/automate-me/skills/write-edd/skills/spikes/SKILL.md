---
name: spikes
description: Run each spike the design depends on as a throwaway prototype, or record why it is blocked, and raise the evidence level from the result. Use as the spike step of write-edd, after the delta list and before the EDD draft.
---

# Spikes

A spike settles one fact the design depends on by running something, not by reading or guessing.

## Inputs

- `out/delta.txt` and the ARCH lines.
- The evidence that already exists (step 5 of the playbook).
- `sandbox.md` in the inputs, if the person wrote one. It names each sandbox a spike may call and how to sign in. No file means no sandbox.

## Step 1. List the spikes

Write one line per fact in `out/spikes.txt`:

```
SPIKE<n>: <one question> | FOR <D, E or A ids that depend on it> | WHY <what changes in the design if the answer is no> | ANSWERS GAP <n>
```

`ANSWERS GAP <n>` is only for a spike that stands in for a PENDING PM question. Leave it off otherwise.

A fact needs a spike when a DELTA, ENABLE or ARCH depends on it, its best evidence is below level 4, and running something could settle it. Facts that only a person can settle are Decisions, not spikes. Skip a fact that changes nothing in the design.

## Step 2. Run each spike

Follow pstack's Prototype playbook (`skills/poteto-mode/playbooks/prototype.md` in the installed `pstack` plugin) when it is installed. In short:

- The smallest script that asks the one question, in a scratch folder outside the project repo.
- No tests, no abstractions. The printed output is the evidence.
- Call only a sandbox named in `sandbox.md`. Never production, never a customer's data, never the project repo's app or commands.

## Step 3. Write the evidence file

One file per spike in `out/evidence/SPIKE<n>.md`, in the format of `templates/evidence.md`.

- It ran: `STATUS: RAN`, with METHOD, WHERE, RESULT (raw output), ANSWER and LEVEL 4. Keep the script next to the file.
- It cannot run now, and the team could run it: `STATUS: PLANNED`, with QUESTION, METHOD and WHERE, and `ANSWERS: GAP <n>` when it stands in for a PENDING PM question. No RESULT, ANSWER or LEVEL. Use this for a needed fact that has no answer yet.
- Something outside the team stops it: `STATUS: BLOCKED` and `BLOCKED: <the reason, and what would unblock it>`. No ANSWER. A missing sandbox, a missing credential or a needed person are reasons. "Not enough time" is not, and it is PLANNED.

## Step 4. Feed the result back

- A hazard backed by a spike that ran takes level 4 and cites the SPIKE id.
- A hazard backed by a planned or blocked spike keeps its old level and cites the SPIKE id, so the reader sees what would settle it. A planned spike never raises a level.
- A DELTA that rests on a planned or blocked spike says `ASSUMES SPIKE<n>`. The decisions table gets a row for each planned spike. The row names those deltas and says it is a spike.
- An answer that contradicts a DELTA or ARCH stops the run. Report it to the person. Do not redesign here.

Check. `check_edd.py spikes` passes after the draft.
