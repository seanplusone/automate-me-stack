# Score: run-1

Run on 2026-10-22 against an earlier version of the `automate-me` plugin, the same way as `preset-field` run-1. Each scenario ran in a fresh agent (Opus) with only `SKILL.md`, `repo/`, the scenario's diff and its description, away from the key.

| Scenario | Want | Got | Script |
|---|---|---|---|
| by-hand | FAILS at step 3 | A1 FAILS at step 3, picks `CsvWriter::download` and `row` over `cursor()`, as the order export does | PASS |
| uses-writer | HOLDS | A1 and A2 HOLD | PASS |
| guard-in-caller | FAILS at step 5 | A2 FAILS at step 5, picks the escaping inside `CsvWriter::row` | PASS |

A person's read of the picked shapes:
- by-hand also names the in-memory `->get()` where the sibling streams with `cursor()`. That is the same shape problem, read correctly.
- guard-in-caller says the order export stays open to formula cells. That is the reason the rule belongs in the writer.
- No run failed `uses-writer` for missing formula escaping, the first trap in the key.

The first scoring failed guard-in-caller on a bare `OrderExportController.php:9` in its reason text, with the verdict right. The scorer now checks only a SHAPE's last field, which the output format reserves for its citation.
