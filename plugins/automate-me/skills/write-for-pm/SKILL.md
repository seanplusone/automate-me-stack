---
name: write-for-pm
description: Draft or rewrite one piece of text a non-technical PM reads, in the PM voice. A comment on a PRD, a correction to a PRD line, a Slack message to the PM, or a single open question. Use for "write this for the PM", "put this in PM voice", or "draft a PRD comment". A full PRD review is review-prd.
---

# Write for a PM

One piece of text in, one draft out. The voice lives in `../shared/voices/pm.md` and the rules in `../shared/writing-rules.md`. This file adds only the steps, so a change to the voice reaches every skill that loads it.

The person posts the draft. This skill never posts, sends, or edits a PRD.

## Run

1. **Load the voice and the rules.** Read `../shared/voices/pm.md` and `../shared/writing-rules.md` in full.
2. **Use the PRD's names.** If a review-prd run exists for this PRD, load its `out/terms.txt`. Otherwise use the names the PRD uses most for the product, the customer and each role. Never use a job title the product has no role for.
3. **Check each fact about today's product.** Read the code or data behind it before it goes in. A fact goes in only when the PM needs it to decide or to fix the PRD, in one plain sentence, with no file names, code, field names or IDs. Keep the evidence (`path:line`) in a note under the draft for the person, never in the draft.
4. **Write the draft.**
   - A question follows the voice's shape: a person at a moment, what they would notice, then the ask.
   - A correction says what the PRD says, then what the product does instead in plain words, then what that changes for the PM, if anything. When the wrong part is only how the product is built, ask the PM to drop or soften the line rather than restate the code. How it is built belongs in the design doc.
   - No proposed answer and no engineering argument (W12).
   - Say where the draft goes. An open question joins the section at the bottom of the PRD. A correction goes inline, as a comment on its line.
5. **Run the writing check.** Save the draft to a file and run `python3 "$SKILL_DIR"/../shared/check_writing.py <file>`. Rewrite only the flagged lines. `$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.
6. **Cold read.** A worker that sees only the draft, and the glossary if there is one, restates what it says or asks. Rewrite once any sentence it could not restate, any phrase it calls technical, and any part that leads to an answer. For a correction, also give the worker the PRD line it sits on, marked as the PM's own words. A term from that line is hers, not jargon, so don't count it as technical.
7. **Return** the draft, then the evidence note, then anything not verified.

## Enforced by

- The writing check: `check_writing.py` (step 5).
- A second model: the cold read (step 6).
- A person: nothing is posted until the user says so.
