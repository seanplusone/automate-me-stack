# Brief: Review the Pause subscription PRD

- Kind: review
- Plan first: none needed. One PRD, one pass; the skill below has its own steps.
- Goal:
  - Find the gaps in the "Pause subscription" PRD from Dana and draft questions for the PM.
  - The questions go to the PM before the review on Monday.
  - unknown: What should Monday's review decide, whether to build it or only what to change in the PRD?
- Done:
  - Customers pause their plan for up to 3 months instead of cancelling. Proof is the PRD sentence that says so.
  - investigate: What happens to billing while a plan is paused?
  - investigate: Does the renewal date move?
  - investigate: Can a customer pause twice in a row?
  - investigate: Does the PRD cover annual plans?
  - investigate: Does support get a tool to pause or resume a plan?
  - Each investigate item becomes a PM question only if the PRD does not answer it. Proof is the section that does.
  - Questions carry no proposed answer.
- Taste: "Good, not twenty nitpicks." Flag, don't filter. The count needs a number from the speaker.
- Output: One list of questions for the PM, each with the PRD section it is about, read in the reply. A separate list of gaps for engineering.
- Constraints: If the PRD cannot be found, stop and ask for the link. Report only: draft the questions, change nothing in the PRD, message no one.
- Tools:
  - unknown: Is the PRD at docs/prd/pause-subscription.md? The speaker said "I think".
  - write first: none until that path is confirmed. Read the file before drafting questions.
- Agents and roles: One reviewer drafts the questions. The PM reads them before Monday. No split.
- Run mode: one-at-a-time
- Evals:
  - Pass: a question names a PRD section and offers no answer.
  - Fail: a question states what billing does.
- Verification: Every gap names the PRD section or line behind it, or says guess.
- Skills: review-prd for the gaps and PM questions, or review-prd-light for a lighter pass. None runs yet.
- Parking lot:
  - The pricing page toggle between monthly and yearly. A separate task.
- Unknowns:
  - unknown: Is the PRD at docs/prd/pause-subscription.md? The speaker said "I think".
  - unknown: How many questions at most should go to the PM?
  - unknown: What should Monday's review decide, whether to build it or only what to change in the PRD?

## Questions

1. Is the PRD at docs/prd/pause-subscription.md, or can you share the link?
2. How many questions at most should go to the PM?
3. What should Monday's review decide, whether to build it or only what to change in the PRD?
