# Which skill, when

Find where you are in the work, then type the command. Every skill drafts for you to read. None of them posts a review, approves a PR, or changes a PRD on its own.

## Starting out

| You want to | Type | You get |
|---|---|---|
| Turn a rough idea into a prompt | `/automate-me:outcome` | Your ramble sorted into a one-line-per-slot brief, with at most 3 questions only you can answer. Nothing runs until you say yes. |
| Set the project up | `/automate-me:setup` | Your databases, tracker, test commands and local app detected and confirmed, then written to `.claude/`. Run it again to change anything. |

## Working a ticket

These need `.claude/project-profile.md`, which `/automate-me:setup` writes. Ticket keys look like `PROJ-123`.

| You want to | Type | You get |
|---|---|---|
| Start a ticket | `/automate-me:working-rules fix PROJ-123` | A worktree, the ticket read and validated, then a checkpoint page with the cause, fix options and test plan. It stops at three checkpoints for your answers. |
| Carry on in a new session | `/automate-me:working-rules pickup PROJ-123` | Where the ticket stands, from its worktree's `RESUME.md`, then it continues. |
| Stop for now | "pause safely" | The step finished, a `wip:` commit, and `RESUME.md` updated for the next pickup. |
| Test in the browser | `/automate-me:verify-web` | A health check of your local app, then the change driven in the real app, with screenshots kept as evidence. Needs `.claude/verify-web.yaml` (from `/automate-me:setup`). |
| Look at data | `/automate-me:query-db` | A read-only query on the default (non-prod) environment, or the database and environment you name, e.g. `/automate-me:query-db analytics prod`. Needs `.claude/query-db.json`. |
| Open the PR | `/automate-me:open-pr` | The prose check, one confirmation, then a draft PR linked to the ticket. |

`working-rules` typed with no command only loads the rules for whatever you ask next.

## Reviewing a PR

| You want to | Type | You get |
|---|---|---|
| Understand a doc or a PR before reviewing it | `/automate-me:explain-doc <path or PR link>` | One page that shows the big picture through a small example and the flow in stages. It sums up every section and lists what looked wrong. |
| Check a PR does what its test plan says | `/automate-me:verify-web pr <PR number>` | Each scenario run on the base branch and the PR branch, with evidence. A `verify.md` marks each one VERIFIED, CONTRADICTED or NOT RUN. |
| Review a PR | `/automate-me:review-pr <PR link>` | At most five short inline comments per PR and a verdict, on a page you can share. Results from `verify-web pr` go in as findings. Nothing is posted until you say so. |
| Know if a PR is too big | `/automate-me:split-pr <PR link or branch>` | A size verdict and, if it should split, which files go in each smaller PR and in what order. |
| Write one comment or reply | `/automate-me:write-for-engineer` | One draft in the engineer voice, with the evidence behind each claim. |

## Before the code: PRD and design

| You want to | Type | You get |
|---|---|---|
| Review a PRD | `/automate-me:review-prd` | Open questions for the PM, as one section at the bottom of the PRD, plus inline corrections. |
| A lighter PRD pass | `/automate-me:review-prd-light`, then `/automate-me:find-prd-collisions` | What is unclear or missing, then points that contradict each other and scenarios nothing covers. |
| Write one PM message | `/automate-me:write-for-pm` | One draft a non-technical PM can answer. |
| Design the change | `/automate-me:write-edd` | A draft EDD from the reviewed PRD, with today's code traced, the blast radius, and spikes run or marked blocked. |

## Good to know

- Three skills start only when you type them: `setup`, `working-rules` and `open-pr`. Claude can reach for the others on its own when they fit.
- `query-db` never writes to prod, whatever is asked. It hands you the SQL instead.
- Nothing needs pstack. If you have it, `working-rules` and the spikes in `write-edd` use its playbooks. The README says how to install it.
- What each skill is made of, and its checks, is in the README's Layout section.
