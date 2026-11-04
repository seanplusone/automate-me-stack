# automate-me-stack

Claude Code skills that take a change from the PRD to a reviewed PR. They review the PRD, design the EDD, prove the change in the running app, and review the PRs that implement it. Each skill holds its output to scripted checks, and the scored ones have practice cases you can run.

```
PRD  ->  review-prd  ->  PM answers  ->  write-edd  ->  you approve  ->  implementation  ->  verify-web  ->  review-pr
```

New here? [GUIDE.md](GUIDE.md) says which skill to use when, and what to type.

## Origin

I built these skills while working as an engineer on a production SaaS product, where they ran on real PRDs, design docs and pull requests. This repo is a generalized copy made for public use:

- Product names, internal systems, tickets and infrastructure details are removed.
- Skills that were tied to one company's stack (`query-db`, `working-rules`, `verify-web`) are rebuilt around a config file for your own project, which `/automate-me:setup` writes for you.
- Eval cases that came from real reviews are replaced with synthetic ones, and every scorer still runs against them.

## Install

This repo is a Claude Code plugin marketplace named `automate-me-stack` that holds one plugin, `automate-me`.

```
/plugin marketplace add seanplusone/automate-me-stack
/plugin install automate-me@automate-me-stack
```

Update later with `/plugin marketplace update automate-me-stack`, then `/plugin update automate-me@automate-me-stack`.

Every skill is named verb first and loads as `/automate-me:<name>`.

| When you want to | Type |
|---|---|
| Find the gaps in a PRD and the questions for its PM | `review-prd` |
| Do a lighter PRD review, gaps only | `review-prd-light` |
| Find PRD points that contradict each other | `find-prd-collisions` |
| Write the EDD for a reviewed PRD | `write-edd` |
| Understand a long doc or a large PR before reviewing it | `explain-doc` |
| Review one PR, or a set of linked PRs | `review-pr` |
| Prove a change, or a PR's test plan, in the running web app | `verify-web` |
| Split a branch or PR that is too big to review | `split-pr` |
| Commit a change and open it as a draft PR linked to its ticket | `open-pr` |
| Query one of your Postgres databases, read-only by default | `query-db` |
| Configure a project for these skills (databases, tracker, tests, web app) | `setup` |
| Write something a PM will read | `write-for-pm` |
| Write something an engineer will read | `write-for-engineer` |
| Turn a colleague's ask into claims, proposals, fix options and tests before running anything | `decode-ask` |
| Load a set of working rules for this session | `working-rules` |
| Check and tighten a draft prompt before an agent runs it | `brief-check` |

The skills under `shared/skills/` run inside those, not on their own. Their names match the EDD steps they fill: `current-state`, `blast-radius`, `design-options` and `panel-check`.

## Set up for your project

Most skills work as installed. Four read a file from your project's `.claude/` folder. The quick way is to run this once in the project:

```
/automate-me:setup
```

It detects what it can from the repo (default branch, test command, local ports, Postgres services, database env variable names and MCP servers, never secret values). Then it asks a few multiple-choice questions, checks the answers and writes the files below. Run it again to change them. To do it by hand, copy each example from the skill's folder:

| Skill | Copy | To | What it holds |
|---|---|---|---|
| `query-db` | `query-db.example.json` | `.claude/query-db.json` | Named databases and their environments, marking the default and prod. Each connects through a read-only Postgres MCP server, a `psql` service, an env variable, or your own tunnel command. No passwords. |
| `working-rules` | `project-profile.example.md` | `.claude/project-profile.md` | Tracker and ticket format, base branch, worktree setup, test commands, local app URL |
| `open-pr` | the "Opening a PR" section of `project-profile.example.md` | `.claude/project-profile.md` | Ticket URL, review status, reviewer, project board, labels |
| `verify-web` | `verify-web.example.yaml` | `.claude/verify-web.yaml` | App URLs, test logins by role, health checks, workers, evidence folder |

When you pick a Postgres MCP connection and none exists, setup can add one to `.mcp.json`, with credentials only as `${VAR}` references. Point it at a read-only login.

`verify-web` drives the browser through an MCP server: [Playwright MCP](https://github.com/microsoft/playwright-mcp) by default, or Chrome DevTools MCP.

### Optional: pstack

Nothing here needs pstack. If you have it installed, the spikes step in `write-edd` follows its Prototype playbook, and `working-rules` layers on top of `/pstack:poteto-mode`. To install it:

```
/plugin marketplace add cursor/plugins
/plugin install pstack@cursor-plugins
```

## Layout

Everything lives under `plugins/automate-me/skills/`:

- `review-prd/` finds gaps in a PRD and runs `find-prd-collisions` on them. It checks every question and every rewrite against the PRD and the product's code, and uses the PRD's own names. Engineering questions and defects go to a separate list. It asks the PM only what the engineer would otherwise have to guess, one situation per question with no proposed answers. The questions go in one block from `templates/open-questions.md`, added at the bottom of the PRD. `cases/crm-sync-sample` scores it on an invented PRD.
- `review-prd-light/` and `find-prd-collisions/` are the lighter PRD review pair. The first finds gaps. The second runs after it and finds points that contradict each other and scenarios no point covers.
- `write-edd/` writes a draft EDD with blast radius, evidence, spikes (run or blocked with a reason) and two mermaid diagrams built from the delta list. `cases/order-sync` is an invented PHP repo and PRD, scored by `check/check_all.sh`.
- `verify-web/` proves a change in the running web app the way a user would see it. Its `doctor.py` is read-only and config-driven. It checks the health URLs and any containers and workers you list. It also catches a worker that started before the last change to its code, and a page and background jobs that run different code trees. Then it drives the screens through the browser MCP and keeps evidence: snapshots, screenshots, console errors and failed requests. Each side effect is checked a second way. `verify-web pr <number>` reads a PR's test plan and runs each scenario on the base branch, then the PR branch. It writes `verify.md` with a VERIFIED, CONTRADICTED or NOT RUN verdict per scenario, for `review-pr` to use. `cases/demo-app` is a small invented web app with a PR that claims a fix it doesn't make.
- `query-db/` runs read-only Postgres queries on the databases named in `.claude/query-db.json`, for example `query analytics prod`. The default is the non-prod environment. Prod is used only when named in that message, and prod writes are always refused. Before the first query on each database and environment, `guard.sql` counts the tables the login can write to, and the skill refuses a read-only environment whose login can write. `check/check_config.py` rejects a config that allows prod writes or holds a secret. `check/test_guard.py` proves the guard on two throwaway databases.
- `setup/` configures a project for `query-db`, `working-rules`, `open-pr` and `verify-web`, in the style of pstack's setup. `detect.py` reads the repo and reports each value with the file it came from, never a secret value. The skill asks, validates with each skill's own checker, and writes whole files, so a rerun updates them. It runs only when typed.
- `explain-doc/` turns a long design doc, PRD, runbook or PR into one page a reader can follow without opening the source. `check/check_map.py` holds the map to its limits, a cold read on a smaller model checks it, and `check/render_page.py` renders the page. It explains only; it judges nothing and posts nothing.
- `review-pr/` reviews one PR or a set of linked PRs and drafts at most 5 short inline comments per PR, with a verdict. `check/check_drafts.py` holds it to that length. Checks for each file type load from `references/`. `cases/refund-endpoint` and `cases/auth-header` score it on invented PRs. Nothing is posted until a person says so.
- `split-pr/` says whether a branch or PR is too big to review well and, if so, plans the stack of PRs it becomes. `check/size.py` owns the thresholds and fails a plan that misses a file, puts one in two slices, or would revert a newer change on the base. It plans only.
- `open-pr/` commits the change on a ticket branch and opens it as a draft PR linked to the ticket in your tracker. Reviewer, project board and labels are optional settings. It stages only the files the change touched and confirms the title, message and file list once before it writes anything. It runs only when typed.
- `decode-ask/` turns a colleague's message into one short page before anything runs. The page lists what they want decided, each claim in system terms, each proposal, and each test with the result that would change the answer. Tests then run one per turn after a go, and the reply is drafted from the results.
- `working-rules/` holds working rules for a session: response style, scope, verification, process, review voice and delegation. `fix <ticket>` and `pickup <ticket>` run a ticket from worktree to draft PR with checkpoints, using the values in `.claude/project-profile.md`. `check/check_profile.py` fails when a placeholder the rules use is missing from the profile, and `--filled` fails a value still left as a placeholder. It loads only when typed.
- `write-for-pm/` and `write-for-engineer/` are standalone writing skills: one piece of text in, one draft out, in the matching voice from `shared/voices/`.
- `brief-check/` scores a draft prompt on six slots (plan first, goal, checks, output, verify, if stuck) and flags common traps. It fixes mechanical gaps and runs the prompt, or stops and asks when a gap needs information only the user has.
- `shared/` holds what all of them use:
  - `writing-rules.md` and `check_writing.py`, plus `pr_prose.py`, which runs the same check over the comments, markdown, commit messages and body a PR publishes.
  - `client_sweep.py`: finds every repo and client that reads a changed key, searching each `--repo` you pass by the key's name, the value's shape and the payload it travels in. `working-rules fix` runs it before any "no effect" claim.
  - `voices/`: who a draft is written for. `engineer.md` is the voice for PR review comments, and `pm.md` is for questions a non-technical PM reads.
  - `skills/current-state`: how the code does one thing today, step by step with file:line.
  - `skills/blast-radius`: what fires, filters or depends on one entity. `check_blast.py` checks both lists against the code.
  - `skills/design-options`: proposes a design, or judges one, starting from what already exists. `cases/preset-field` and `cases/csv-export` score its judge mode with `check/score_judge.py`.
  - `skills/panel-check`: several reviewers with different lenses, a skeptic, and a blind judge mode for scoring.
  - `playbooks/learn-from-run.md`: turns misses into proposed rules. A person approves each one.
  - `check_shared.py`: fails when a `../` path or link does not resolve, when a shared skill names the skill that calls it, or when a script is not called as `"$SKILL_DIR"/<path>`.

## Checks

Every check prints PASS or FAIL and exits 1 on FAIL. Run `sh setup.sh` once after cloning (it makes the `write-edd` practice repo its own git repo), then from `plugins/automate-me/skills/`:

```
python3 shared/check_shared.py
for t in $(find . -name 'test_*.py'); do (cd "$(dirname "$t")" && python3 "$(basename "$t")" >/dev/null) || echo "FAIL $t"; done
```

`query-db/check/test_guard.py` needs a local Postgres or a pulled `postgres:16` image and prints SKIP without one. The `verify-web` PR case needs Node with Playwright.

## Credits

Ideas adapted, with credit, from pstack by Lauren Tan (MIT): the `how`, `architect`, `blast-radius` and `reflect` skills, the Eval playbook, and the encode-lessons principle. Also from Cursor's `continual-learning` plugin (MIT).

Every rule names what enforces it: a script, a second model, or a person.

## License

MIT. See [LICENSE](LICENSE).
