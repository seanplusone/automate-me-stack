# Playbook: eval gap

A review lens for `review-pr`, not a skill of its own. Load it from `review-a-pr.md` step 2 when the diff touches a model registry, a prompt, or a gate on model output, or when the profile names `eval_gate`. It asks whether an eval exercises the same checks production runs, and whether a model default changed without an eval run.

The playbook is generic. It never names a domain, a language, or a project's grammar. Domain rules live in the project, behind the project's own eval command and golden cases.

## Extension point

One profile key, `eval_gate`, names the project's pieces. A project fills this in; the playbook does not invent paths.

```
- `eval_gate`:
  - registry: <path to the model default or registry>
  - gate: <path#function of each production check on model output, comma-separated>
  - eval: <offline command>, <live command>
  - golden: <path to the golden cases>
```

Example shape (paths are illustrative):

```
- `eval_gate`:
  - registry: lib/ai/models.ts
  - gate: lib/ai/outputGate.ts#evaluateOutputGate, lib/ai/generate.ts#evaluateCandidateGates
  - eval: npm run eval:golden -- --gate-only (offline), npm run eval:golden (live)
  - golden: scripts/evals/golden.json
```

With no profile key, search the diff and the repo for the same four pieces and say what you found. A missing eval or a missing gate is itself a finding.

This playbook does not add an eval framework, a scorer registry, or a CI template. It asks the questions and runs the project's own commands.

## Steps

1. **Find the production gate.** List every deterministic check production applies to model output before it reaches a user (schema, format, domain rules). Name each function and the path it lives at. Read the production call path, not a comment that describes it.

2. **Find the eval.** List what the project's eval scores. A production gate the eval never calls is a `should fix` finding at `PR`, with the gate's name.

3. **Golden cases.** Every past production rejection that can be reproduced becomes a golden case, run through the production gate function itself. Live text that was never logged is marked inferred, never measured. A golden set that only checks format, while production also runs a quality gate, is the same finding as step 2.

4. **Model change trigger.** If the diff changes a model default and nothing runs the eval on that path, that is a `should fix` finding. Ask for a trigger on the model registry path, and for a graceful skip when the provider key is absent.

5. **Measure once.** Run the eval on the old and new model config with the same cases, and put both pass rates in the drafts `Body:` as that one allowed extra sentence, not a separate essay. Use the offline command when it exists and is enough. If the live command needs a provider key that is not set, skip with `skip: no provider key` and still file findings from steps 2 to 4. If both configs fail the same way, the model swap did not cause the failure, so say so.

Findings from this lens go into the candidates of `review-a-pr.md` step 6, then through classify, draft and the refuter like any other.
