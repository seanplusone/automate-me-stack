---
name: open-pr
description: Commit the current branch's change and open it as a draft PR linked to its tracker ticket, then move the ticket to review. Reads the ticket key from the branch name and the title from your tracker. Use for "commit and open the PR", "open a draft PR for this ticket", or the PR step at the end of a ticket fix.
disable-model-invocation: true
---

# Initial commit and draft PR

## Project settings

These live in your project's `.claude/project-profile.md` (the same file `working-rules` reads), so a plugin update never overwrites them. Run `/automate-me:setup` and pick "project profile" to fill them in, or copy the "Opening a PR" section of `../working-rules/project-profile.example.md`. Leave a line blank to skip that part.

- `ticket_key_format`: the ticket key pattern, such as `PROJ-123` (letters, a dash, digits)
- `tracker`: Jira, Linear, GitHub Issues, or another. Name the CLI or MCP tool you use for it.
- `base_remote` and `base_branch`: where the PR opens, such as `origin` and `main`
- `ticket_url`: `<tracker-base-url>/<key>`
- `review_status`: the status a ticket moves to when its PR is open (for example `In Review`)
- `default_reviewer`: `<reviewer-handle>`
- `project_board`: `<owner>/<project-number>`
- `labels`: `<label>`, and when each applies

Read them from `.claude/project-profile.md`, or from the project's `CLAUDE.md` if that is where they live. Where a value is blank, skip the step that uses it.

## 1. Ticket key

Take the key from `git branch --show-current` (`PROJ-123-add-export` or `feature/PROJ-456-x` gives `PROJ-123` / `PROJ-456`). No key in the branch name: ask for it.

## 2. Ticket title

If the ticket is already in context, use it. Otherwise read it from your tracker. For Jira with `acli`, run `acli jira workitem view PROJ-{n}` and read the `Summary:` and `Status:` lines; for Linear or GitHub Issues, use its CLI or MCP tool (for example `gh issue view {n}`). A ticket whose description is a table can read badly in CLI text mode; use the tracker's MCP tool for that one. Tool missing or failing: ask for the title.

## 3. Stage only the change

Run `git status --short`. Stage the files this change touched, by path. Never `git add -A` or `git add .`: the main checkout carries untracked notes and docs that are not part of any PR. An untracked file you did not create for this change stays out; list it in the confirmation so the user can say otherwise.

When the change is already committed on the branch and nothing is left to stage, skip staging and the commit in step 6. The PR opens from those commits.

## 4. Check the prose

Write the commit message (step 5's shape) and the PR body to files, then run the prose check from the repo root. `$SKILL_DIR` is the base directory this skill prints when it loads, and `<base>` is `git merge-base <remote>/<base branch> HEAD`.

```bash
python3 "$SKILL_DIR"/../shared/pr_prose.py <base> --message <message-file> --body <body-file>   # change staged
python3 "$SKILL_DIR"/../shared/pr_prose.py <base> HEAD --body <body-file>                        # change already committed
```

It checks every comment and markdown line the change adds, the commit messages and the body, against the `[script]` rules in `../shared/writing-rules.md`. Fix each hit where it lives: a code comment in its source file, then stage it again; a message or body line in its draft. Rewording a commit that already exists rewrites history, so ask first.

Then read the same lines against the `[judgment]` rules in `../shared/writing-rules.md`, and against the repo's own comment rules when it has them (such as a `CLAUDE.md` or `.claude/rules/` file). The script checks none of those.

## 5. Confirm once

Draft all of it, then show it in one message and wait for a yes or edits:

- PR title: `[PROJ-{n}] {title}`, from the ticket summary, sharpened if the summary is vague.
- Commit message, from the staged diff:

  ```
  [PROJ-{n}] {title}

  Fixes: <ticket-url>

  {what changed and why}
  ```

- Base: `base_branch` from the profile, unless the user named another. With no profile value, ask.
- The staged file list, and any untracked files left out.
- The prose check: passed, or each line you changed.

## 6. Commit, push, open the draft

PRs live on the org repo. Use `base_remote` from the profile when it is set. Otherwise: in a fork checkout `upstream` is the org and `origin` is the fork, so push to `upstream`; with no `upstream` remote, push to `origin`.

```bash
REMOTE=$(git remote | grep -qx upstream && echo upstream || echo origin)
REPO=$(git remote get-url "$REMOTE" | sed -E 's#.*[:/]([^/]+/[^/]+)$#\1#; s#\.git$##')
BRANCH=$(git branch --show-current)

git commit -F <message-file>
git push -u "$REMOTE" "$BRANCH"
gh pr create --draft --repo "$REPO" --head "$BRANCH" --base {base} \
  --title "[PROJ-{n}] {title}" --body-file <body-file> \
  --assignee @me   # add --reviewer <reviewer-handle> when the project settings name one
```

The body is the commit message without its first line, so the `Fixes:` link is in it. When the change was already committed, the body is the one checked in step 4, with the same `Fixes:` link. When the project settings name labels or a project board, add them: `gh pr edit <pr-url> --add-label <label>` and `gh project item-add <project-number> --owner <owner> --url <pr-url>`.

Always open it as a draft. The user marks it ready.

## 7. Ticket

Assign the ticket to yourself and move it to the review status from the project settings, with your tracker's tool. For example, with Jira and `acli`:

```bash
acli jira workitem assign --key PROJ-{n} --assignee "@me"
acli jira workitem transition --key PROJ-{n} --status "<review status>" --yes
```

Skip the transition when the ticket is already there, or when no review status is set. Either call failing (already assigned, transition not allowed) gets one line in the reply and does not fail the run; the PR exists.

## 8. Reply

The full PR URL first, then the ticket's new status.

## Enforced by

- The prose check: `../shared/pr_prose.py` (step 4).
