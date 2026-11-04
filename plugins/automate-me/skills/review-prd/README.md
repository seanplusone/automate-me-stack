# review-prd

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`.

Reviews a PRD point by point and lists what is unclear or missing. It works with plain Claude. No other tooling is needed.

Status: working. A question reaches the PM only when, without an answer, the engineer would have to guess what a user or customer notices. The questions live in one block, added as one section at the bottom of the PRD, with no proposed answers. Each covers one situation, with up to three related asks. The list is sized to one review meeting. `check.py pm-list` warns past 25, and the skill merges or drops by the test, never by rank. The report is a short note for the engineer. After the gap step it runs `../find-prd-collisions` to catch points that contradict each other and scenarios between points.

Version notes. Steps 7 to 11 of the playbook exist because first-draft questions often fail a cold reader or misquote the PRD. Every rewrite goes back through steps 7 and 8, and the PRD's own terms go to `out/terms.txt`. A noun that names more than one thing is marked ambiguous. The cold reader flags rereads and technical phrases, and step 13 gives the engineer a review page. `check.py terms` and `check.py premise` catch a wrong product or customer name, an ambiguous noun, and a report question that skipped step 8.

Known gap: collisions and card picks vary between runs (one run finds a blank-value overwrite, the next does not), so one run can drop a find. Expect to tune over more PRDs.

In 0.6.2 the block follows `templates/open-questions.md`, checked by `check.py open-questions`. The glossary names terms in plain words instead of the PRD's labels. A question the PRD's own open questions ask stays when engineering's plan changes the answer, and two questions merge only when one answer settles both. ANSWERED searches the whole PRD. At most 20 questions go to the PM. A row gets at most two rewrites before it goes to the reviewer. The examples moved out of the skill into its case.

## Layout

```
review-prd/
  README.md                 this file
  SKILL.md                  orchestrator: runs the playbook, reports back
  playbooks/
    review-a-prd.md         the steps, start to finish
  skills/
    prd-mindmap/SKILL.md    builds the map
    prd-gaps/SKILL.md       finds the gaps
  templates/
    open-questions.md       the block added as one section at the bottom of the PRD
  rules/
    expected-sets.json      CRUD and feature lifecycle
    prd-basics.json         asked on every PRD, purpose first
    sync.json               fires when two systems share data
  check/
    README.md               what the check script must verify
    check.py                the checks
    score_case.py           scores a run's gaps against a case key
    test_check.py           tests for check.py and score_case.py
  cases/
    crm-sync-sample/
      input/prd.md          the only thing the skill is given
      key.md                the known gaps, kept away from the skill
      runs/run-1/           one saved run
      runs/score.md         the scores of every run
```

## Run it

1. Give the skill only `cases/<name>/input/`. Never give it `key.md`.
2. Save its output in `cases/<name>/runs/run-<n>/`. A saved run is a record. Never edit it. A later fix shows up in a new run.
3. Run the checks in `check/README.md` on the output.
4. Score it and add a column to `cases/<name>/runs/score.md`.

## Score a run

Run `python3 check/score_case.py cases/<name>/key.md <run>/gaps.txt`. It prints found or missed for each key gap. A key row with a `Terms:` line counts as found only when a gap on its point names every term. Without one, any gap on that point passes, even one about a different problem. Give every key row a `Terms:` line.

Record three numbers per run.

- Found and missed, from the script. A person still checks that each found gap asks the key's question.
- Unsupported. Gaps in the output with no PRD quote behind them. These count as errors. `check.py gaps` finds them.

If the output has a gap that is not in `key.md` but does have a quote, a person decides whether it is real. If it is, add it to the key with a `Terms:` line.

Runs of one version differ. Score at least two runs of each version before reading a difference between versions.

## Add a case

1. Make `cases/<name>/input/prd.md`.
2. Write `cases/<name>/key.md` in the same format as the existing one.
3. Use invented PRDs only. Do not commit a real PRD or its key.

## Why the key is separate

If the skill can see the key, the score means nothing. Run it from a copy of the case without `key.md`.
