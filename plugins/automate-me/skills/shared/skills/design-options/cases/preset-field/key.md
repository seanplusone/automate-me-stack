# Key: preset-field

Three changes to one invented form library, each judged on its own in JUDGE mode. Never show this file to the skill.

The repo, the diffs and this key are invented. `repo/` is the code before each change. A form field has a definition (`src/Fields/`) and a renderer (`src/Render/`). The form builder's palette (`builder/`) already has presets: a palette entry that fills in an ordinary field, so the runtime never sees it. `YesNoPreset` is the one sibling.

## How to run

For each scenario, give the skill `repo/`, `inputs/<scenario>.diff` and `inputs/<scenario>.md`, in JUDGE mode, and save its output. Then run, from this folder:

```
python3 ../../check/score_judge.py key.md <scenario> <output.txt> .
```

It checks the SHAPE verdicts, the step a FAILS names, and that every cited file:line exists in `repo/` or in the scenario's diff. A person then reads whether each FAILS picks the right shape.

## Expected shapes

| ID | Scenario | Verdict | Step | Cites one of | Why |
|----|----------|---------|------|--------------|-----|
| K1 | new-kind | FAILS | 3 | `builder/presets/`, `src/Fields/SelectField.php` | A Priority field is a select with three settings filled in. Presets already do that (`builder/presets/YesNoPreset.php:6`), so a new field kind and renderer are a second way to do one task. |
| K2 | preset | HOLDS | - | - | It mirrors `YesNoPreset`. The runtime never learns it exists, and the repeater rule already lives in the base (`builder/presets/Preset.php:14`). |
| K3 | preset-leaks | FAILS | 5 | `src/Render/SelectRenderer.php`, `src/Fields/SelectField.php` | The preset itself holds, but the select definition and renderer now know a preset's name. The runtime would render the same without knowing it, so a style belongs in a select setting the preset fills. |

## Traps

- Calling the new preset in `preset` a new kind of thing. A preset is a configured select, and the palette already has one.
- Passing `preset-leaks` because its preset mirrors `YesNoPreset`. The failure is in the runtime files it also changed.
- Asking `preset` to add its own repeater check. The base already carries it, so adding one per preset is the step 5 failure, not the fix.
