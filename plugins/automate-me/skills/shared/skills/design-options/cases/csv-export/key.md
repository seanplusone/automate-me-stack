# Key: csv-export

Three changes to one invented web app, each judged on its own in JUDGE mode. Never show this file to the skill.

The repo, the diffs and this key are invented. They have a different shape from the skill's own example, so a pass shows the steps carry over. `repo/` is the code before each change. `src/Support/CsvWriter.php` streams a CSV download, and `OrderExportController` is the one export that uses it. Each change adds an invoice export.

## How to run

Copy `SKILL.md`, `repo/`, `inputs/<scenario>.diff` and `inputs/<scenario>.md` into an empty folder, so the key is out of reach. Run the skill there in JUDGE mode in a fresh session and save its output. Then run, from this folder:

```
python3 ../../check/score_judge.py key.md <scenario> <output.txt> .
```

A person then reads whether each FAILS picks the right shape.

## Expected shapes

| ID | Scenario | Verdict | Step | Cites one of | Why |
|----|----------|---------|------|--------------|-----|
| K1 | by-hand | FAILS | 3 | `src/Support/CsvWriter.php`, `src/Http/OrderExportController.php` | It builds the CSV by hand, with its own quoting and headers, beside a writer that already streams one. It also loads every invoice into memory where the sibling streams them. |
| K2 | uses-writer | HOLDS | - | - | It mirrors `OrderExportController` line for line and uses the writer. |
| K3 | guard-in-caller | FAILS | 5 | `src/Support/CsvWriter.php` | Formula escaping must hold for every export. Put only in this controller, the order export stays open to it, and the next export has to remember it. It belongs in `CsvWriter::row`. |

## Traps

- Failing `uses-writer` for a missing feature such as formula escaping. The change does not claim it, and judging what a change should have added is not its shape.
- Passing `guard-in-caller` because it uses the writer. The failure is where the escaping lives.
- Calling `guard-in-caller` a step 3 miss. Nothing escapes cells today, so there is no precedent to reuse. The writer is where the new rule goes.
