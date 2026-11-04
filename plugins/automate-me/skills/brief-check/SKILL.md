---
name: brief-check
description: Use when the user runs /brief-check with a draft prompt, or asks to check, review, or tighten a prompt before an agent runs it. Fixes mechanical gaps and runs it; stops and asks when a gap needs info only the user has. For a rough idea with no draft yet, write the goal in two sentences first, then run this.
---

# Brief check

Review the user's draft prompt, fix it, and run it when it's safe to.
Goal: better results now, and better prompt-writing habits over time.

## Style
- Concise and direct. Short sentences. No em dashes.

## Step 0: Is a review worth it?
If the task is small, quick, and easy to redo (a typo fix, a one-line
change, a quick lookup), say "Fine as is" and run it. Don't review.

## Step 1: Score the slots
Show a small table: ✅ clear, ⚠️ vague, ❌ missing.

1. Before you start (big or ambiguous tasks only): ask questions and
   show a plan first?
2. Goal: what to do AND what decision the user will make with the result.
3. Must-haves / Check: each rule is checkable, with named proof
   (test run, file and line, doc section, photo).
4. Output: what comes back, how many, which fields.
5. Verify: how claims get proved. Must include "every claim names
   the run or file:line behind it, or says guess."
6. If stuck: what to do when the goal can't be met. Loops need a cap.

## Step 2: Check for traps (one line each, only if present)
- Adjective with no proof: modern, valid, correct, clean. Turn it
  into a visible signal or an example.
- Judgment call with no example: suggest one yes and one no example,
  described in words (links go stale).
- Unknown treated as no: rules need yes / no / unknown (flag it).
- Hard rule vs taste: taste should be "flag, don't filter."
- Side effects with no guardrail: if the agent could push, comment,
  message, or edit, add "Report only" unless the user wants action.
- Vague scope: "the PRs," "the spec." Name links, branches, paths.
- Tool not named: if a check needs a browser, a test run, or images,
  say so, and check the tool actually works first.
- Stale context: facts that may have changed since they were written.

## Step 3: Decide: fix and run, or ask

Mechanical gaps (fix them yourself):
- Missing slot labels or structure
- Missing evidence rule (slot 5)
- Missing "Report only" guardrail
- Missing output format, when the right one is obvious

Gaps only the user can fill (stop and ask):
- Which decision the result is for
- Scope: which PRs, files, spec, or branch
- Limits: budget, caps, deadlines
- Anything that would make you guess at intent

If every gap is mechanical:
1. Show the table and the top fixes in 3 lines or fewer.
2. Show the fixed prompt.
3. Run it.

If any gap needs the user:
1. Show the table.
2. Ask only the questions you need, numbered, in one message.
3. Wait. After they answer, fix the prompt and run it.

Never fill a gap only the user can fill with a guess.
