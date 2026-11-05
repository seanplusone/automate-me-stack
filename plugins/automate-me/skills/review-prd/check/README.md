# Check script spec

`check.py` implements checks 1, 3, 5, 6 and 9 to 17. `test_check.py` tests checks 10 to 17, the usage lines and `score_case.py`. Check 4 is partial (tag format only). Checks 2, 7 and 8 are not written yet. Use any language the team already runs.

## Inputs

- The skill's output file.
- The PRD it reviewed (`cases/<name>/input/prd.md`).
- `../../shared/rules/expected-sets.json`.

`check.py` never reads `key.md`. `score_case.py` scores a run against the key, and a person checks its found gaps (see the main README).

Every script prints its usage and exits 0 on `-h`. A missing argument or unknown command prints the usage and exits 2.

## Checks

Each check prints PASS or FAIL. Any FAIL fails the run.

1. **Quotes.** Every quoted line in the output appears word for word in the PRD. Normalize whitespace only. No fuzzy matching.
2. **Six answers.** Every point has all six answers. Each is a quote or the exact text `not stated`.
3. **Gaps.** Every gap has a point number and an owner. The owner is one of `PM`, `Engineer`, `Unclear wording`.
4. **Tags.** Every point has exactly one tag from `create`, `read`, `update`, `delete`, `none`, and one quote.
5. **Groups.** Every point sits in exactly one outline group.
6. **Scenarios.** `check.py scenarios` lists every scenario the rules produce: a missing CRUD operation, plus each `prd-questions` rule (for example feature lifecycle). `check.py check-scenarios` fails if the output drops one or adds one. This is the only place "missing" is decided.
7. **Counts.** The counts at the end of the output match what the body contains.
8. **Empty PRD.** If the PRD has no points, the output must say so and nothing else.
9. **Writing.** `check.py writing` checks the `[script]` rules in `../shared/writing-rules.md` on `out/open-questions.md`. It skips `Quote:` lines, because those are the PM's words.
10. **PM list.** `check.py pm-list` checks the questions in `out/open-questions.md`. Each is one situation with one to three asks (question marks), and no two have the same ask. None uses a jargon-list word, and the purpose question comes first when it is asked. Past 25 questions, one review meeting's worth, it prints a WARN line without failing.
11. **Sort.** `check.py sort` checks `out/questions.txt` against `out/open-questions.md`. Every row has one tag from `PM`, `DESIGN-DOC`, `ANSWERED`, `DROP`, an intent and a reason. A PM reason starts "We would guess" and names what a user or customer would notice. An ANSWERED reason is a PRD quote, or quotes joined by ` + `. Every question in the block has a PM row, matched by its ask.
12. **Premise.** `check.py premise` checks `out/premise.txt` against `out/open-questions.md`. Every question has at least one `<question> | <noun or claim> | <evidence>` row, so a rewrite that skipped step 8 fails. No question relies on a noun marked `ambiguous`.
13. **Terms.** `check.py terms` checks `out/terms.txt` against the PRD. The file exists and has `product` and `customer` rows. Each term is used in the PRD at least as often as each other name listed for it. With the block given, no question uses one of the other names.
14. **Open questions.** `check.py open-questions` checks `out/open-questions.md` against `templates/open-questions.md`. The heading is "Questions from engineering (<name>, <month>)". The intro line is exactly "Please answer under each question." and nothing else. The glossary has 1 to 6 terms, and there is a "Biggest decisions" group of at most 8. Questions are numbered as bold text, with no proposed answer, point number, section number or file path. There is no cap on how many. With `out/prd-labels.txt` given, no question uses one of the PRD's labels outside "the PRD calls it".
15. **Gaps.** `check.py gaps` checks `out/gaps.txt`. Every gap has a point number, an owner and a PRD quote. A scenario answered by a line that puts the decision off (TBD, a working assumption) has a gap that quotes it.
16. **Carry.** `check.py carry` checks `out/carried.txt`. Every PM or Unclear wording gap in `out/gaps.txt` points at a row in `out/questions.txt`, even a DROP. A gap found and then never sorted fails.
17. **Fresh.** `check.py fresh` compares the PRD the review read with the PRD fetched again before the draft goes out. It fails and lists each sentence removed or added. Spacing and list markers are not a change.

## Open item

Check 2 needs the six answers written out. `prd-gaps` counts them but does not list them yet, so the count cannot be verified.
