# PM answers

One line per PM question from review-prd, plus one line per correction engineering posted on the PRD. Copy the GAP number and question exactly. The PM's answer is quoted word for word. Do not reword it.

```
ANSWER GAP <n>: <question> | "<PM's words>" | <date>
PENDING GAP <n>: <question> | asked <date>
CORRECTION C<n>: <the PRD statement, quoted> | <what the code does, with file:line> | posted <date> | OPEN|ACCEPTED|REJECTED
```

Rules:
- An answer that does not settle the question stays PENDING, with a note on what is still unclear.
- A PENDING line does not stop the run. edd-draft turns it into a row in the decisions section (the `decisions` role in the layout). The row's default is engineering's position. The row names every DELTA that rests on the answer (`ASSUMES GAP <n>`). The owner is the PM, unless the input names someone else.
- A planned spike can stand in for a PENDING answer, said out loud. The spike names it with `ANSWERS: GAP <n>` (see `templates/evidence.md`). The line here stays PENDING.
- A CORRECTION says the PRD is wrong about how the product works today. The EDD follows the code, not the corrected statement.
- OPEN means the PRD owner has not answered. ACCEPTED means the PRD owner agrees the PRD is wrong. REJECTED means the PRD owner says the PRD is right.
- The EDD lists every C id in the section named by the `prd_record` role. For OPEN and REJECTED, that line also says what the design assumes.
- A CORRECTION with no file:line fails `check_edd.py delta`.
