# Key: eval-gap

A synthetic case. The repo `acme/text-app` and PR #88 are invented, and so is every line number below. The PR changes a default model in `lib/ai/models.ts`. Never show this file to the skill.

The project's eval scores schema and format of model output. Production also runs `evaluateOutputGate` in `lib/ai/outputGate.ts` before a result reaches a user. Of 295 outputs the eval passed, production rejected 52. The PR does not add a CI trigger on the registry path. The ticket is PROJ-410, "Swap the default model."

- acme/text-app#88 at `0000000b2` (fake head)

## How to score

- Run `python3 check/score_case.py cases/eval-gap/key.md <drafts.md>`. It checks that each finding has a comment on the right path, within 3 lines of the row's Line when it names one.
- A person then checks that each found comment names the same problem. Wording can differ.
- A comment with no evidence behind it is **unsupported** and counts as an error.
- The run passes the format only if `check/check_drafts.py` exits 0.

## Findings the skill should make

| ID | PR | Path | Line | Finding | Min sites | Proof |
|----|----|------|------|---------|-----------|-------|
| K1 | text-app#88 | PR | - | The eval scores schema and format, and never calls the production gate `evaluateOutputGate`. Production rejected 52 of 295 outputs the eval passed. | - | The eval command list and `evaluateOutputGate` at the PR head. |
| K2 | text-app#88 | `lib/ai/models.ts` | 12 | The diff changes the default model, and nothing runs the eval when this file changes. Ask for a trigger on the registry path, and a skip when the provider key is absent. | - | The workflow files have no path filter on `lib/ai/models.ts`. |

Terms: K1 | gate | eval
Terms: K2 | default/model | eval

Optional finds. A question or nit on these is fine, and missing them is not a miss.

- The new default has no recorded pass rate on the golden cases in the PR body.

## Traps

- Saying the eval is missing. An eval exists; it scores the wrong checks.
- Saying production has no gate. `evaluateOutputGate` already runs on the live path.
- Anchoring the missing-gate finding on `lib/ai/models.ts`. That finding has no line in the diff, so it sits at `PR`.
