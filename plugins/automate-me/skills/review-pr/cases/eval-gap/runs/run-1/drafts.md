# PR review: eval missed a model change

The eval still scores schema only, so a model swap can pass the eval while production rejects a large share of the same outputs.

## acme/text-app#88 | approve after the eval calls the production gate
About: Changes the default model used to generate text for the user.
Changes: 3 files: 2 source, 1 test

### should fix | PR | https://github.com/acme/text-app/pull/88
The eval scores schema and format, and never calls `evaluateOutputGate`. Production rejected 52 of 295 outputs the eval passed. Can the eval call that gate?
Plain: The eval and production do not run the same checks. A model change can look fine in the eval while production drops many of the same results before a user sees them.
Evidence: Production rejected 52 of 295 eval-passing outputs at the PR head.
Step: measured | The eval command scores schema and format only.
Step: measured | evaluateOutputGate rejected 52 of those 295 outputs.
Step: inferred | A default-model swap can ship with no eval signal from that gate.

### should fix | lib/ai/models.ts:12 | https://github.com/acme/text-app/pull/88/files#diff-942f73d13d403391f92998e05dbb5f0b94a0f02b01239a4df9eb685ace879dbaR12
This changes the default model, and no workflow runs the eval when this file changes. Can a job run the eval on this path, and skip when the key is absent?
Plain: The registry can change and CI will not run the eval, so a bad default can merge with no measured pass rate. A missing provider key should skip the job, not fail the build.
Evidence: No workflow path filter includes lib/ai/models.ts.
Step: measured | The default in lib/ai/models.ts:12 changed.
Step: measured | No CI workflow lists that path as a trigger.

Body: The eval needs to call the production gate before merge, and the other comment is inline. Both defaults scored 40/40 on generation and 20/40 on the gated path, so the swap did not cause the gap.

## Totals
Refuter: checked 2, reworded 0, dropped 0.
