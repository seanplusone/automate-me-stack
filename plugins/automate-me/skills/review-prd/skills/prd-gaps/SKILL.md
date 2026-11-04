---
name: prd-gaps
description: Find what a mapped PRD leaves unclear or missing. Use after prd-mindmap, as part of a PRD review.
---

# PRD gaps

Input is an approved map from `prd-mindmap` plus the PRD. Find the gaps. Do not design anything.

## Step 1. Ask six questions of each point

1. Who triggers it?
2. What exactly happens?
3. Where does the data live, and where does it go?
4. When does it run?
5. Why does it exist?
6. What happens if it fails?

Answer only with a word-for-word PRD quote, or `not stated`.

Check. Every point has six answers. None is a guess.

## Step 2. Tag the operation

Tag each point with one of: create, read, update, delete, none. Quote the line that shows it.

Do not decide what is missing. The check script compares tags to `rules/` and lists what is missing.

## Step 3. Fill rule scenarios

`$SKILL_DIR` is the review-prd folder, which holds `check/`. Run `python3 "$SKILL_DIR"/check/check.py scenarios out/gaps.txt "$SKILL_DIR"/rules out/map.txt`. Copy each printed line into the output word for word, replacing the last field with the PRD quote that answers it, or `not stated`. Add no scenarios yourself.

Check. `check.py check-scenarios` passes: every rule scenario is present, and none is invented.

## Step 4. Sort each gap

Every `not stated` answer and every `not stated` scenario is a gap. So is every answer that puts the decision off (TBD, to be decided, a working assumption), and every line with two readings. `check.py gaps` fails a scenario that puts the decision off with no gap quoting it. Give each gap an owner:

- PM. A product decision.
- Engineer. A technical call for the design doc.
- Unclear wording. Write both readings.

If the answer decides what a user sees, waits for or loses, the PM owns it, even when engineering builds it.

Check. Every gap has a point number and an owner. `python3 "$SKILL_DIR"/check/check.py gaps <prd> out/gaps.txt` passes.

## Output format

```
TAG: R<n> | <operation> | <quote>
SCENARIO <n>: <rule> | <scenario> | <quote or "not stated">
GAP <n>: R<n> | <question> | <owner> | <quote or "not stated">
COUNTS: points <n>, answers <n>, scenarios <n>, gaps <n>
```

## Limits

- Checks each point alone, plus the rule scenarios. Nothing else.
- No facts about outside systems unless the PRD or a linked source says it. Otherwise `unverified`.
- Do not read the codebase.
