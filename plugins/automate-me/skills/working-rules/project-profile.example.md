# Project profile

Run `/automate-me:setup` to fill this in from what it finds in the repo, or copy this file to `.claude/project-profile.md` in the project repo and replace every `<...>`. The working-rules skill and its fix playbook read a value here wherever they write `<profile: ...>` with that key. Keep one ``- `key`: value`` line per key, so the skill finds it. Delete a line the project does not need, and the skill asks when it hits that step.

## Tracker

- `tracker`: `<Jira with acli | Linear MCP | GitHub Issues with gh>`
- `ticket_key_format`: `<PROJ-123: letters, a dash, digits>`
- `ticket_search`: `<acli jira workitem search --jql 'project = PROJ AND summary ~ "<words>"'>` or `<gh issue list --search "<words>">`
- `ticket_view`: `<acli jira workitem view <KEY>>` or `<gh issue view <n>>`
- `ticket_comments`: `<acli jira workitem comment list --key <KEY>>` or `<gh issue view <n> --comments>`

## Git

- `base_remote`: `<origin, or upstream when origin is your fork>`
- `base_branch`: `<main>`
- `worktree`: `<yes | no: branch in place for repos that cannot run from a worktree>`
- `worktree_copy`: `<gitignored files each worktree needs as real copies, e.g. .env, vendor/, node_modules/, a local config file>`
- `worktree_check`: `<a command that proves the worktree runs its own code, e.g. php -r "require 'vendor/autoload.php'; echo (new ReflectionClass(App\\Kernel::class))->getFileName();">`

## Tests

- `test_one`: `<the command that runs one test class or file from the worktree, e.g. pytest tests/test_orders.py, or npx jest src/orders.test.ts>`
- `test_full`: `<the command that runs the full suite against the worktree>`
- `test_notes`: `<anything a run needs: run migrations first with ..., the suite runs in a container named ..., split a full run by folder because ...>`

## Local app

- `app_url_test`: `<http://localhost:3000, the local site that is safe for test data and imports>`
- `app_url_other`: `<other local sites, and what they must not be used for>`
- `clients`: `<every client that reaches the code: web app, mobile app repo, public API, queued jobs>`
- `client_repos`: `<one NAME=PATH per client checkout to search, e.g. web=., mobile=../mobile-app, worker=../jobs>`

## Review

- `review_skill`: `<the repo's own review skill or command, e.g. /team:review, or none>`
- `change_checklist`: `<the repo's change checklist or blast-radius file, e.g. .claude/blast-radius.md, or none>`

## Opening a PR (read by open-pr)

Leave a line blank to skip that step.

- `ticket_url`: `<tracker-base-url>/<key>, e.g. https://example.atlassian.net/browse/<key> or https://linear.app/<team>/issue/<key>`
- `review_status`: `<the status a ticket moves to when its PR opens, e.g. In Review>`
- `default_reviewer`: `<reviewer GitHub handle, or blank>`
- `project_board`: `<owner/project-number for gh project item-add, or blank>`
- `labels`: `<label, and when each applies, or blank>`
