# Score: run-1

Run on 2026-10-22 against an earlier version of the `automate-me` plugin. Each scenario ran in a fresh agent (Opus) with only `SKILL.md`, `repo/`, the scenario's diff and its description copied into an empty folder, so the key was out of reach.

| Scenario | Want | Got | Script |
|---|---|---|---|
| new-kind | FAILS at step 3 | A1 FAILS at step 3, picks a preset like `YesNoPreset` | PASS |
| preset | HOLDS | A1 HOLDS, mirrors `YesNoPreset`, inherits the repeater rule | PASS |
| preset-leaks | FAILS at step 5 | A2 FAILS at step 5, picks a style setting on the select that the preset fills | PASS |

A person's read of the picked shapes:
- new-kind also says the new field kind escapes the base's repeater rule (step 5). That is true and a fair extra.
- new-kind and preset-leaks both read "the priority style" as a second capability and pick a style setting on the select that knows nothing about presets. That is the shape the key's K3 names.

Limit. The skill's own example is a preset that fills a select, the same shape as this case. `csv-export` is a case of another shape, and its run-1 passes too.
