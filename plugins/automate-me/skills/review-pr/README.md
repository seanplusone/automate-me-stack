# review-pr

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`.

Reviews one PR, or a set of linked PRs, and drafts short inline comments with a verdict per PR. Nothing is posted. The user reads the page, then says whether to post it as a pending review.

Status: working. The review attacks by default. It re-runs claims and keeps a finding only with a file and line or a breaking input it ran. Five synthetic scored cases. `cases/refund-endpoint` and `cases/auth-header` score comment drafts. `cases/trust-report`, `cases/word-score` and `cases/item-cap` each hide one planted bug, and `check/score_case.py` passes only when the attack file catches it. The original comment cases came from real reviews on a production codebase and were replaced with synthetic ones for public release.

`--sandbox auto` uses `bwrap` whenever it is installed. A reachable `key.md` runs only in that sandbox. `--sandbox none` cannot override a practice run. A checkout with no `key.md` may use `--sandbox none`, which prints a warning. The agent sees system libraries, a fresh `/tmp`, and a home that receives only login files. Session transcripts stay on the host.

## What keeps it short

`check/check_drafts.py` fails a drafts file when:

- a comment is over 50 words (the message says to cut a clause, not the articles);
- an evidence line is over 25 words;
- a PR has more than 5 findings or more than 1 nit comment;
- a comment joins two halves with a colon (W2);
- a verdict or heading is not in the fixed shape;
- a verdict holds with no `blocking` finding, or does not hold with one;
- a `Sites:` line is not `<n> | <command>`;
- a finding has more than one `Plain:` line, or one over 110 words;
- the shared `[script]` writing rules fail.

`check/check_attack.py` fails an attack file when:

- the json block is missing or does not match the schema;
- the file says approve but a tried row broke, a finding remains, or nothing was tried;
- the verdict is approve and the case key says `Planted: yes`.

## Layout

```
review-pr/
  README.md                  this file
  SKILL.md                   orchestrator: the drafts format, the page, the chat reply
  playbooks/
    review-a-pr.md           the steps, start to finish
  references/
    attack.md                the attack brief, the attack file, and the merge rule
    infra.md                 scripts, CI, IAM, cloud resources, the CLI stub
    claude-config.md         .claude/ rules, skills, settings, plugins and marketplaces
    docs.md                  runbooks, ADRs, design docs
    frontend.md              TypeScript/React, shared API clients, store hygiene, JS in server templates
    bundle.md                committed build output from another repo
  check/
    cli.py                   shared usage/exit helper the other scripts import
    classify.py              labels each changed file source, test, generated, asset or docs
    attack_agents.py         finds codex or claude on PATH and runs one headless pass each
    check_attack.py          fails an attack file that tried nothing, or approved a planted bug
    check_drafts.py          the format and writing check
    merge_attacks.py         matches file and line, and keeps either pass's finding
    live_state.py            fails on a closed PR or a head that moved since the review
    moved_drift.py           lists what a moved file is missing from its source
    post_review.py           posts a checked drafts file to GitHub, only when told
    render_page.py           renders a checked drafts file as the review page
    summary.py               the summary message, as Markdown or Slack mrkdwn
    score_case.py            scores drafts, or a planted bug by a judge or by location
    test_*.py                plain-script tests: python3 check/test_<name>.py
  cases/
    refund-endpoint/         one Python PR: a line row with Terms, a directory row with a site minimum, a PR-level row
      key.md                 expected findings and traps
      runs/run-1/drafts.md   hand-written drafts (passes, 3 of 3)
      runs/score.md
    auth-header/             two linked TypeScript PRs in one drafts file
      key.md                 expected findings, a site minimum and an a/b term
      runs/run-1/drafts.md   fails on purpose: a sampled site count and a comment outside the line window
      runs/run-2/drafts.md   the same drafts with both misses fixed (passes, 3 of 3)
      runs/score.md          why run-1 fails, and both scorer outputs
    trust-report/            a report check that trusts a self-reported passed field
      key.md                 Planted: yes, plus the Catch terms
      pr.md                  the PR body, including a pass claim
      diff.patch             the small diff
      runs/run-1/passes/current.md  the single pass, before the merge
      runs/run-1/attack.md   the attack file from that pass
      runs/run-1/trace.txt   the commands and the output they printed
      runs/score.md
    word-score/              a scorer that passes keyword-stuffed text
      key.md
      runs/run-1/attack.md
      runs/score.md
    item-cap/                a cap of 5 written as less-than 5
      key.md
      runs/run-1/attack.md
      runs/score.md
```

Run the drafts check on a case: `python3 check/check_drafts.py cases/refund-endpoint/runs/run-1/drafts.md`.

Score a drafts run against its key: `python3 check/score_case.py cases/auth-header/key.md cases/auth-header/runs/run-1/drafts.md`.

Score an attack run against a planted bug: `python3 check/score_case.py cases/trust-report/key.md cases/trust-report/runs/run-1/attack.md`.
