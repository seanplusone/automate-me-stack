# Evidence file

One file per probe or spike. A probe reads existing behavior. A spike tries a new call against a sandbox. Hazards in the EDD cite these by id.

```
ID: PROBE<n> or SPIKE<n>
STATUS: RAN, BLOCKED or PLANNED
BLOCKED: <only when blocked: the reason, and what would unblock it>
ANSWERS: <only when planned, and only when it stands in for a PM question: GAP <n>>
QUESTION: <one question this answers>
METHOD: <exact steps or command, so someone else can rerun it>
WHERE: <environment, never production or a customer>
RUNNER: <only person: a probe the team cannot let the agent run, such as a read replica>
RESULT: <what happened, with raw output or a link to it. May run over several lines>
ANSWER: <one sentence answer to QUESTION>
LEVEL: <2 to 5, see below. Text after the digit is fine>
DATE: <yyyy-mm-dd>
BY: <person>
```

Rules:
- A field runs until the next line that starts a new `FIELD:`, so RESULT can take many lines. ID is its first word, so `SPIKE2 (PROJ-2 P0-3)` is SPIKE2.
- A RAN file has LEVEL 2 to 5. Reading is evidence too. For a probe or spike: 2 cited a line or a doc, 3 walked the path in source, 4 ran a query or code, 5 reproduced it in the running app.
- A hazard that claims level 4 or 5 must cite a RAN PROBE or SPIKE whose LEVEL is at least that high. A level 2 or 3 file backs a level 2 or 3 hazard.
- WHERE names no production or customer. A phrase like "never a customer org" is fine. A probe that must read production sets `RUNNER: person`, says `read-only` in WHERE, and is run by a person, never by the agent. The checker reports it as person-run.
- A claim marked "verify" stays unverified until a file with ANSWER exists.
- RESULT is the raw output. ANSWER is the reading of it. Keep them separate.
- A BLOCKED file has no RESULT, ANSWER or LEVEL. It cannot raise a hazard's level.
- A PLANNED file is a spike the team can run but has not run yet. It has QUESTION, METHOD and WHERE, and no RESULT, ANSWER or LEVEL. It cannot raise a hazard's level. Use BLOCKED instead when something outside the team stops the spike.
- A DELTA that rests on a planned or blocked spike says `ASSUMES SPIKE<n>`. The EDD's decisions table gets a row for each planned spike, naming those deltas and saying it is a spike.

## How sure are we (evidence levels)

Adapted from pstack's `blast-radius` skill (MIT). Every hazard in the EDD names its level.

1. Said so. Not allowed as evidence.
2. Pointed at the line: a real file:line.
3. Walked the failure step by step and showed whether it reaches.
4. Ran it: a probe or spike called the real code.
5. Reproduced it in the running app.
