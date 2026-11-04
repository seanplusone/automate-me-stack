---
name: write-for-engineer
description: Draft or rewrite one comment or message an engineer reads, in the engineer voice. A PR comment outside a full review, a review body, a reply in a PR thread, or a Slack message to a teammate about code. Use for "write this as a review comment" or "put this in my voice for the engineer". A full PR review is review-pr.
---

# Write for an engineer

One piece of text in, one draft out. The voice lives in `../shared/voices/engineer.md` and the rules in `../shared/writing-rules.md`. This file adds only the steps, so a change to the voice reaches every skill that loads it.

The voice is for review comments and short messages about code. Design-doc and EDD prose follows the team's own standard, not this skill.

The person posts the draft. This skill never posts a comment, approves a PR, or sends a message.

## Run

1. **Load the voice and the rules.** Read `../shared/voices/engineer.md` and `../shared/writing-rules.md` in full.
2. **Check each claim in the code.** Read the code at the ref under discussion (the PR head, or the branch the person names) before a claim goes in. A claim you did not check becomes the question, as the voice says.
3. **Write the draft** in the voice's shape. First a fact about the code that names the file, value or behaviour. Then the ask, as a direct question with the fix in it when the fix is known. One point per comment. No pleasantries, no softeners, no reason tacked onto the ask.
4. **Run the writing check.** Save the draft to a file and run `python3 "$SKILL_DIR"/../shared/check_writing.py <file>`. Rewrite only the flagged lines. `$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.
5. **Return** the draft, then the evidence for each claim (`path:line` at the ref you read), then anything not verified.

## Enforced by

- The writing check: `check_writing.py` (step 4).
- A person: nothing is posted until the user says so.
