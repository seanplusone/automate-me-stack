---
name: find-prd-collisions
description: After a review-prd-light run, find PRD points that contradict each other and user scenarios that no point covers. Use when the user says "check this PRD for collisions", "what scenarios are missing", or after a PRD review.
---

# PRD collisions

review-prd-light checks each point on its own. This skill checks points against each other, and looks for scenarios that fall between them. Do not design anything. Do not decide behavior.

## Step 1. Load the points

Use the numbered points from the review-prd-light output, or from `out/map.txt` when review-prd calls this skill. Keep their numbers. If there is neither, run review-prd-light's Step 1 first.

Check. Every point has its number and a word-for-word quote from the PRD.

## Step 2. Group points by what they share

List the things the PRD names: people (roles), things (items, lists, accounts), events (invite, delete, pay), and numbers (limits, times, counts). Under each one, list every point that mentions it. A point can sit under several.

Check. Every point is under at least one entry.

Why. Two points can only collide if they touch the same person, thing, event or number.

## Step 3. Find contradictions

Inside each group, take every pair of points. Ask: can both be true at once, for the same person and the same thing? Look for:

- One allows what the other forbids.
- Same event, different results.
- Two numbers or limits for the same thing that disagree.
- Order or timing that cannot both hold.
- One applies to "all" or "any", the other excludes some.
- An answer in the PRD's questions-and-answers section disagrees with the line it answers. The answer is the PM's latest word, so raise it to get that line fixed.

For each contradiction write both point numbers, both quotes, and one short scenario where they collide. Build the scenario only from words in the PRD.

Check. Write the number of pairs you compared. Every contradiction has two point numbers and two word-for-word quotes.

## Step 4. Find scenarios no point covers

For each person and each thing from Step 2, walk through these moments:

1. The first time.
2. Empty, or none yet.
3. At the limit, or over it.
4. Done twice, or by two people at once.
5. Undone, cancelled, or reversed.
6. The person leaves, is removed, or loses access.
7. A state from one point meets a rule from another point.

For each moment, find the point that says what happens. Quote it. If no point does, write "not covered" and the scenario in one sentence, built from PRD words. Cite the points whose words you used.

Check. Every "not covered" cites at least one point number. No scenario uses a word the PRD does not contain, except the moment words above.

## Step 5. Drop repeats and sort owners

If a finding is already in the review-prd-light gap list (or review-prd's `out/gaps.txt`), mark it "already in review, gap N" and leave it out of the new lists.

Sort the rest with the same owners as review-prd-light:

- **PM.** A product decision. Most contradictions land here.
- **Engineer.** A technical call for the design doc.
- **Unclear wording.** The line can be read two ways. Write both readings.

Then read each PM question as the PM. If answering it needs knowing how the system is built, move it to Engineer. If it decides what a user sees, waits for or loses, keep it with the PM even when engineering builds it.

Check. Every finding has an owner. No PM question names storage, servers, APIs, sync, caches or code.

## Step 6. Write the output

Use the same headings as the review-prd-light output, so both lists merge into one. If the review output is in the same file, add your items under its headings, marked "(collision)", instead of writing a second set.

1. **Questions for the PM.** Write them in `../shared/voices/pm.md`. Each numbered question asks for one decision, ends in "?", cites its point numbers, and names a person, a moment and a choice. Follow-ups go under it as lettered sub-questions, at most 3. At most 15 numbered questions across both skills.
2. **For the design doc.** The Engineer findings, one line each, with point numbers.
3. **Can't tell.** Write "none" if empty.
4. **Not checked.** Every step or guard that was skipped, with its reason. Write "none" if empty.
5. **Counts.** Points, groups, pairs compared, contradictions, uncovered scenarios, repeats dropped, questions for the PM.
6. **Detail.** The groups, then contradictions (number, both point numbers, both quotes, the scenario, the owner), then uncovered scenarios (number, the scenario, the cited points, the owner).

Check. A contradiction means both points cannot hold at once. A case where no point says what happens is an uncovered scenario, even when it involves two points.

## Hard requirements

- Start with a todolist. The six steps above are its items, copied in word for word.
- A step you skip stays in the list as `skip: <reason>`. Silent skipping is not allowed.
- The run fails if any quote is not word for word in the PRD. No "..." inside a quote.
- The run fails if any finding has no point number or no owner.
- If the PRD or its points are missing, stop and say so. Do not invent content.

## Guards

- Never edit the PRD. Never contact the PM. The user does both.
- If you hand work to another model, give it file pointers, not pasted text.
- You own what a delegate returns. Read its actual output, not its summary.
- Have a different model re-check the contradictions against the PRD. If the two disagree, show the user both.

## Limits

- Do not read the codebase. Do not propose solutions.
- A finding that fits no step goes under "Other observations", marked as having no PRD quote.
