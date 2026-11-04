---
name: panel-check
description: Review a draft with several independent reviewers, each with one lens, then keep only findings that survive a skeptic. Use on a PM question list, an EDD, or any draft before a person sees it. Also scores test runs blind.
---

# Panel check

One reviewer misses what a second lens would catch. This runs several, then filters hard so the person only sees what is real.

Adapted from pstack's `reflect` skill and Eval playbook (MIT, Lauren Tan), and from the common practice of reviewing a PR with a panel of reviewers. The ideas taken are parallel lenses, a premise attacker, and a skeptic score per finding. Findings that several lenses agree on weigh more.

## Input

- The draft to check.
- Its inputs, as file paths: the PRD map, answers, code, whatever the draft was built from.
- The lenses. The calling playbook names them.

## Step 1. Run the lenses in parallel

One reviewer per lens, all started at once. Each reviewer:
- Gets file paths, not pasted text, and never the drafter's reasoning.
- Reads the real sources. It does not trust the draft's own descriptions.
- Returns findings in this format:

```
FINDING <lens>-<n> | <item id or file:line> | <what is wrong> | <evidence>
```

Use different models across lenses where you can. If only one model family is available, vary the model size and the lens prompt.

Scale to the draft. A short list needs 2 or 3 lenses. An EDD wants 4 or more, and always the premise lens: "what must be true for this to work at all?", attacked against the real sources.

## Step 2. Score each finding with a skeptic

A separate skeptic reads the sources for each finding and scores how sure it is that the finding is real:

- 0: false under light checking.
- 25: might be real, could not check.
- 50: real, but minor or rare.
- 75: checked, likely to matter.
- 100: confirmed directly by the sources.

Keep findings scored 80 or more. Record how many were dropped and why. Never drop silently.

Also rate reach: does the problem actually happen, or does something already prevent it? A real problem that cannot happen is low priority. Name what prevents it.

## Step 3. Synthesize

- Merge duplicates across lenses.
- A finding raised by 2 or more lenses weighs more. A single-lens finding must clear a higher bar.
- When two lenses disagree, show both and make a reasoned call. Do not average them away.

## Output format

```
KEEP <n> | <lens(es)> | <score> | <item id or file:line> | <what is wrong> | <fix>
DROPPED | <count> | <main reasons>
DISAGREE | <lens A says> | <lens B says> | <call and why>
```

## Blind judge mode (for scoring test runs)

To score a run against a case key:
- The judge sees outputs only by neutral labels, never which model or person made them.
- The judge gets the key and the scoring rules from the case.
- The person who wrote the key does not score the run.
- Read the judge's result yourself, and compare it to the key by hand.

## Guards

- Read only. Reviewers never edit the draft.
- Nothing here is sent anywhere. The person decides.
