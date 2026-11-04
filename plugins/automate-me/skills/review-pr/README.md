# review-pr

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`.

Reviews one PR, or a set of linked PRs, and drafts short inline comments with a verdict per PR. Nothing is posted. The user reads the page, then says whether to post it as a pending review.

Status: working. Two synthetic scored cases (`cases/refund-endpoint`, `cases/auth-header`). The original cases came from real reviews on a production codebase and were replaced with synthetic ones for public release.

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

## Layout

```
review-pr/
  README.md                  this file
  SKILL.md                   orchestrator: the drafts format, the page, the chat reply
  playbooks/
    review-a-pr.md           the steps, start to finish
  references/
    infra.md                 scripts, CI, IAM, cloud resources, the CLI stub
    claude-config.md         .claude/ rules, skills, settings, plugins and marketplaces
    docs.md                  runbooks, ADRs, design docs
    frontend.md              TypeScript/React, shared API clients, store hygiene, JS in server templates
    bundle.md                committed build output from another repo
  check/
    cli.py                   shared usage/exit helper the other scripts import
    classify.py              labels each changed file source, test, generated, asset or docs
    check_drafts.py          the format and writing check
    live_state.py            fails on a closed PR or a head that moved since the review
    moved_drift.py           lists what a moved file is missing from its source
    post_review.py           posts a checked drafts file to GitHub, only when told
    render_page.py           renders a checked drafts file as the review page
    summary.py               the summary message, as Markdown or Slack mrkdwn
    score_case.py            scores a drafts file against a case key's findings, lines, terms and site counts
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
```

Run the check on a case: `python3 check/check_drafts.py cases/refund-endpoint/runs/run-1/drafts.md`.

Score a run against its key: `python3 check/score_case.py cases/auth-header/key.md cases/auth-header/runs/run-1/drafts.md`.
