# Reference: security

Load when the diff touches logging, CI workflows, request or model-input parsers, or code that feeds model output into a later prompt, a shell, or a query. A single-reviewer run uses this list. A panel security lens uses the same classes.

## Risk classes

**Secrets and PII in logs or artifacts.** Log lines, test fixtures, CI artifacts, review pages and eval output must not carry secrets, tokens, API keys or personal data. A redaction that leaves enough of a secret to recover it is still a leak. Grep the diff for log calls, dumped request bodies, and files written under a temp or evidence path, then read what they actually interpolate.

**ReDoS on user input.** A regex that runs on user text, upload names, or model output needs a bound on backtracking. Look for nested quantifiers, overlapping alternation, or a pattern that can fail to match only after a long scan. To measure, run the pattern against a long, almost-matching string in a subprocess with a short timeout. A hang or a timeout is a finding. A dry read of the pattern is not enough to call it safe.

**CI `pull_request_target` and unpinned actions.** `pull_request_target` runs in the base repo's context. Combined with a checkout of the PR head, a fork PR can run its own code with the repo's secrets. Read every workflow the diff adds or edits. An action or container tag that is not pinned to a sha can move under the same name. `pull_request` from a fork already exposes secrets named in that event; say so only when this PR newly writes one.

**Model output fed into prompts or shells.** Text a model produced is untrusted input. Find every call that interpolates it into a later prompt, a shell command, a SQL string, or a template. A boundary (a schema parse, an allow-list, a non-shell API) can make it safe; the finding is the call that has none.

## Measuring

Do not run CI, and do not call a real provider. For a regex, run it in a local subprocess with a timeout. For a log or artifact leak, read the line and say which field is interpolated. For a workflow, quote the trigger and the checkout step. For model output, quote the call that would pass it on.

## Leave alone

A secret name (an env var, a `${VAR}` reference) is not a leak. A risk the author has named and bounded in this PR is the change doing its job, unless the bound does not hold.
