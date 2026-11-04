---
name: review-prd-light
description: Review a PRD point by point and list what is unclear or missing. Use when the user hands over a PRD, or says "review this PRD".
---

# PRD review

Read a PRD and find the gaps. Do not design anything. Do not decide behavior.

## Step 1. Split the PRD into points

A point is one thing the PRD says the system should do.

- Number each point. Copy its line from the PRD exactly.
- Mark background text as "context" and leave it out of the points.

Check. Every sentence in the PRD is either in a point or marked context.

Why. Gaps hide in sentences nobody looked at.

## Step 2. Ask six questions of each point

For each point, answer these:

1. Who triggers it?
2. What exactly happens?
3. Where does the data live, and where does it go?
4. When does it run?
5. Why does it exist?
6. What happens if it fails?

Answer only from the PRD. Quote the line that answers each question. If nothing answers it, write "not stated".

Check. Every answer is a quote or "not stated". No answer is your own guess.

Why. A quote can be checked against the PRD. A guess cannot.

## Step 3. Sort each "not stated"

- **PM.** A product decision. Example: who wins when two edits collide.
- **Engineer.** A technical call that belongs in the design doc. Example: how to detect a loop.
- **Unclear wording.** The PRD can be read two ways. Write both readings.

Check. No "not stated" is left unsorted.

Why. It tells the user who to ask, and it keeps the PM from getting technical questions.

## Step 4. Write the output

Put what the user acts on first and the working last, under these headings in this order:

1. **Questions for the PM.** What the user sends. Write them in `../shared/voices/pm.md`. Merge gaps that ask the same thing and group them by topic, at most 15. Each numbered question asks for one decision, ends in "?" and cites its point numbers. Follow-ups on the same decision go under it as lettered sub-questions (a, b, c), at most 3. Unclear wording goes here as "Did you mean A or B?"
2. **For the design doc.** The Engineer gaps, one line each, with point numbers.
3. **Can't tell.** What the PRD gives too little to judge, such as a screen or document it mentions but does not include. Write "none" if empty.
4. **Not checked.** Every step or guard that was skipped, with its reason. Write "none" if empty.
5. **Counts.** Points, answers, gaps, questions for the PM.
6. **Detail.** The numbered points, the six answers for each, and the full gap list with point number, question, and owner.

Check. Every PM question cites a point number and ends in "?". Every gap in the detail is covered by a PM question, a design doc line, or a "can't tell" line.

## Hard requirements

- Start with a todolist. The four steps above are its items, copied in word for word.
- A step you skip stays in the list as `skip: <reason>`. Silent skipping is not allowed.
- The run fails if any quote is not word for word in the PRD. No "..." inside a quote.
- The run fails if any of the six answers for a point is blank. It must be a quote or "not stated".
- The run fails if any gap has no point number and no owner.
- If the PRD is missing or has no points, stop and say so. Do not invent content.

Why. A pass or fail rule can be checked. "Be careful" cannot.

## Guards

- Never edit the PRD. Never contact the PM. The user does both.
- If you hand work to another model, give it file pointers, not pasted text.
- You own what a delegate returns. Read its actual output, not its summary.
- Have a different model re-check the gap list against the PRD. If the two disagree, show the user both.

Why. Delegated work drifts when nobody checks it. A second model catches different mistakes.

## Limits

- This checks each point on its own. It does not check two points that collide. That needs a separate skill.
- Do not read the codebase. Do not propose solutions.
- If you notice something that fits no step, list it at the end under "Other observations" and say it has no PRD quote.
