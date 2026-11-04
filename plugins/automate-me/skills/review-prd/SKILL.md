---
name: review-prd
description: Review a PRD and draft open questions for the PM, added as one section at the bottom of that PRD, plus inline comments that correct its logic. Use when handed a PRD or asked to review one, and before adding any question or comment to a PRD, so each one passes the answered-or-drop test first.
---

# PRD review

The orchestrator. It runs the playbook, calls the sub-skills, and reports back. It does no analysis itself.

## What the review is for

The PRD is the source of truth for what the feature must do, and the PM owns it. The engineer reviewing it looks for gaps: what is missing, vague or contradictory, so that building it would mean guessing behavior a user or customer would notice. That includes checking the PRD's claims against the product as it is today, since a PRD often assumes work that is already built, or describes it wrongly. It also includes the scenarios the PRD never thought of.

A question goes to the PM only when it passes one test. **Without an answer, the engineer would have to guess what a user or customer sees, is told, waits for or loses.** Everything else is not the PM's. A question about how to build it goes to the design doc. A question whose answer changes nothing is dropped. The list reads the way an engineer would raise it with a PM across a table. Each question covers one situation, related asks stay together, and the list fits one review meeting. There is no cap that cuts by rank. `check.py pm-list` warns past 25, and the fix is merging and the test, never truncation.

The engineer gives feedback, not answers. A question carries no proposed answer, no engineering argument and no code. A fact about the product today appears only when the PM needs it to answer, in one plain sentence. The PRD's wording, structure and style are not the review's business.

The answered list is what the EM, the engineer and the PM sign off on.

## Run

1. Open `playbooks/review-a-prd.md`. Copy its steps into the todolist word for word.
2. Follow the steps. Each one names the sub-skill or script it uses.
3. Report back in the format below. Nothing else.

## The answered-or-drop test for one question or comment

Use this when someone wants to add one question or comment to a PRD outside a full review. Skip the playbook.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

1. Write the question as one row in `out/questions.txt`, as in playbook step 6. Run playbook steps 7, 8 and 9 on that row only.
2. Write it to `out/one.md` as `**1.** <question>`. Run `python3 "$SKILL_DIR"/check/check.py sort <prd> out/questions.txt out/one.md`, `python3 "$SKILL_DIR"/check/check.py premise out/premise.txt out/one.md`, `python3 "$SKILL_DIR"/check/check.py pm-list out/one.md "$SKILL_DIR"/rules` and `python3 "$SKILL_DIR"/check/check.py writing out/one.md`.
3. Only a PM row that passes goes on the PRD, in the open questions section at the bottom. For an ANSWERED row, tell the person which PRD line answers it. A DESIGN-DOC row goes to the design doc. A DROP row stays off, and the person gets its reason.

A comment corrects a line where one side is plainly right. It quotes the wrong line and the line it contradicts, and step 7 finds both in the PRD. Anything else is a question and takes the steps above. A comment about wording or style is dropped.

## Sub-skills

- `skills/prd-mindmap`: builds the map.
- `skills/prd-gaps`: finds the gaps.

## Report back

The PM's questions live in one place: `out/open-questions.md`, the block a person adds as one section at the bottom of the PRD. The report never repeats them. It is for the engineer and stays short.

1. Load `../shared/writing-rules.md`, `../shared/voices/pm.md` and `out/terms.txt` before writing `out/open-questions.md`.
2. The orchestrator writes `out/report.md`. A sub-agent returns the report's content instead, because it can't write report files. Use these sections, in this order. If one is empty, write "None."

```
# PRD review: <PRD name>

**Questions for the PM.** <n> questions in out/open-questions.md, ready to add as one section at the bottom of the PRD.

**Test plan.** <n> questions in out/testplan-questions.md for the bottom of the test plan page, and <n> corrections for it, or "No test plan."

**For the design doc.** <n> questions and <n> defects in today's product, in out/for-engineering.md.

**Already built.** <One line per piece of the PRD the product already has, with where it lives. "None." if nothing.>

**Not verified.** <Facts about outside systems, product nouns not checked in code or data, and anything else not checked.>

**Stopped or blocked.** <Why the run stopped, or rows sent to the reviewer after two rewrites. "None.">

Counts: points <n>, scenarios <n>, gaps <n>, collisions <n>, questions sorted <n> (PM <n>, design doc <n>, answered <n>, dropped <n>), defects <n>.
```

3. `out/for-engineering.md` has three lists, "Design doc questions", "Defects in today's product" and "PRD lines to correct". One or two short sentences each, ending with its point number and at most two file:line citations. Engineer voice, not PM voice. "PRD lines to correct" holds each contradiction where one side is plainly right: the line that is wrong, quoted, and the line it contradicts, quoted. The engineer decides whether to raise it.

4. Run `python3 "$SKILL_DIR"/check/check.py open-questions out/open-questions.md out/prd-labels.txt`, `python3 "$SKILL_DIR"/check/check.py pm-list out/open-questions.md "$SKILL_DIR"/rules <jargon file>`, `python3 "$SKILL_DIR"/check/check.py sort <prd> out/questions.txt out/open-questions.md`, `python3 "$SKILL_DIR"/check/check.py premise out/premise.txt out/open-questions.md`, `python3 "$SKILL_DIR"/check/check.py terms <prd> out/terms.txt out/open-questions.md`, `python3 "$SKILL_DIR"/check/check.py carry out/gaps.txt out/questions.txt out/carried.txt` and `python3 "$SKILL_DIR"/check/check.py writing out/open-questions.md`. A rewrite goes through the playbook's Rewrites section. Rewrite only the lines they flag. The jargon file is the "Jargon for PM questions" section of the project's `.claude/blast-radius.md`, copied into a plain text file. If the project has none, leave the argument off.

## Guards

- A PRD gets exactly two additions. The open questions go in one section at the very bottom of the PRD they belong to. Corrections to the PRD's logic go in inline comments, one on each wrong line. Nothing else is added, removed or changed, and open questions are never comments.
- A linked test plan is its own document with the same two additions. Its corrections are inline comments on the test plan page, and its open questions go in a section at the bottom of the test plan page (playbook step 10a). Nothing about the test plan goes on the PRD page.
- Never post or send anything to the PM. The person adds the section and the comments, or approves the exact wording first.
- Sub-agents get file paths, not pasted text.
- Read what a sub-agent returns, not its summary.
- A step skipped stays in the todolist as `skip: <reason>`.
