# Playbook: Review a PR

Input is one PR, or a set of PRs that link to each other. Output is `drafts.md` and the page built from it, as `SKILL.md` describes. Paths in this file are relative to the skill directory (`review-pr/`). Copy these steps into the todolist word for word. A skipped step stays as `skip: <reason>`.

## Three rules above the steps

**Review the change, not the codebase.** You may read anything the change reaches: what it calls, what calls it, what reads state it writes. You may not widen past that. A finding about a file the PR neither touches nor reaches is an audit. Tell the user in chat; it is not a comment.

**Nothing is posted.** "Review this PR" is not permission to post. Permission to post one PR does not carry to the next PR or to a later round.

**Counts come from raw git.** A hook that compacts git output (rtk does) rewrites what a pipe reads, so `git diff ... | grep -c` returns a wrong count with no error. In every pipeline that reads git output, call `rtk proxy git` when `rtk` is installed, and plain `git` otherwise.

## Steps

0. **Classify the files.** Run `python3 "$SKILL_DIR"/check/classify.py <owner/repo#n> ... --out <dir>/classes.json` for every PR in the set, with `<dir>` the drafts directory. Put each PR's printed line, after the colon, in its `Changes:` line in `drafts.md`. Pick references from its output, not from file names:
   - Any `generated` file loads `references/bundle.md`, in place of `references/frontend.md` for those files.
   - A PR with 0 `source` files gets its review on the link to the source PR, not on the files.
   - A finding never anchors on a `generated` file. The check fails it.

1. **Context before the diff.** For each PR:
   - `gh pr view <url> --json number,title,body,url,headRefName,headRefOid,baseRefName,author,isDraft,mergeable,additions,deletions,files`. Take owner and repo from the URL. Never assume a repo. `mergeable` is often `UNKNOWN` on the first call; ask again before relying on it.
   - Save the body and read the file whole: `gh pr view <url> --json body --jq .body > <dir>/body.md`. Tool output truncates a long body, and the end is where authors list known gaps.
   - Find the local checkout. Pick the remote whose URL matches owner/repo (`git remote -v`); do not assume `upstream` or `origin`. Then `git fetch <remote> <baseRefName> pull/<n>/head:pr-<n>` and set `BASE=$(git merge-base <remote>/<baseRefName> pr-<n>)`. Every `<base>` below is that sha. A local `master` is usually behind and inflates the diff.
   - The ticket and its parent. Look for a ticket key (e.g. PROJ-123) or an issue link in the prompt, the body, the title and `headRefName`. Fetch it read-only from your tracker (Jira, Linear, GitHub Issues) with whatever CLI or connector the session has, for example `gh issue view <n>` for a GitHub issue. A prompt hook may already have fetched keys typed in the prompt; any other key is yours to fetch. With no key anywhere, do not search the tracker for a match; say "no ticket" in the verdict. If a table came back as one run-together line, re-fetch it as markdown. Read only. Write the acceptance criteria down as a list, including any test a ticket comment asks for, so read the ticket's comments too. If there are none, use the parent's scope; if there is none, use the PR body's own claims. Say which you used. A parent next-step the child quietly dropped is a finding. A finding that reopens a decision the parent settled is noise.
   - Linked PRs. If the body or the ticket names a companion PR, review the set together. Each PR's claims get checked against the others. The best finding is often where two PRs disagree. Write down the safe merge order and what breaks if any one PR merges alone or out of order. When a companion has already merged out of order, say in the chat reply what is broken right now. It is not a comment on this PR.
   - Superseded PRs. If the body says it supersedes a PR, read that PR's open threads. Each unresolved one is either fixed in the new set or still a finding. Resolved ones stay closed.
   - Stacked PRs. If the parent merged, read the parent's merged code, not the branch the child was cut from. Confirm `git diff --name-status <base>...pr-<n>` lists only the files this PR owns.
   - Merged-in PRs. When the branch merges other open PRs (`git log --merges <base>..pr-<n>`), or its parent was rebased after the merge, the merge-base diff shows their work too. Review only this PR's own commits (the PR body often names them; otherwise the non-merge commits not reachable from the merged-in heads). Read each merged-in PR that is outside the given set only where it meets this one, and check whether it is approved, draft or marked DNM. A PR that would carry an unapproved one into its base is `blocking`.
   - Tables in the PR body (columns, fields, endpoints, file lists) are claims about the code. Diff each one against the real array, route or tree.
   - Existing threads. Get the index first. `reviewThreads(first:100)` does not paginate, so check `pageInfo.hasNextPage`:
     ```
     gh api graphql -f query='{repository(owner:"<o>",name:"<r>"){pullRequest(number:<n>){reviewThreads(first:100){pageInfo{hasNextPage} nodes{isResolved isOutdated path line comments(first:1){nodes{databaseId author{login} body}}}}}}}' \
       --jq '.data.repository.pullRequest.reviewThreads | (.pageInfo.hasNextPage), (.nodes[] | select(.isResolved|not) | "\(.comments.nodes[0].databaseId) \(.path):\(.line // "outdated") [\(.comments.nodes[0].author.login)] \(.comments.nodes[0].body[0:120]|gsub("\n";" "))")'
     ```
     Then read full bodies only for open threads near your findings: `gh api --paginate "repos/<o>/<r>/pulls/<n>/comments?per_page=100" --jq '.[] | select(.path == "<path>") | ...'`. `--paginate` is required; the default stops at 100. `--slurp` cannot be combined with `--jq`. Always project with `--jq`; bot comments carry kilobytes of markup. Keep each thread's comment id for a `reply`.
   - A bot comment names the commit it reviewed. If the head moved, read the current code before repeating it.
   - Size. Run `python3 "$SKILL_DIR"/../split-pr/check/size.py <base> pr-<n>`. When it says split, say so in the chat reply with its numbers. Size is never a comment.
   - Prose. Run `python3 "$SKILL_DIR"/../shared/pr_prose.py <base> pr-<n> --body <dir>/body.md`. It lints the comments and markdown the PR adds, its commit messages and its body. Each hit is a candidate for the one `nit`, on the line it names; the body and commit messages have no line, so they go in the review body.

2. **Load the references.** Pick by the file types the diff touches, not by the repo name. A PR can load more than one.
   - Shell scripts, CI workflows, Dockerfiles, compose files, IAM policies, infrastructure-as-code or cloud resources: `references/infra.md`. If the repo has its own guardrail skill, load it too.
   - `.claude/` (rules, skills, commands, settings), `CLAUDE.md`, or a Claude Code plugin or marketplace: `references/claude-config.md`.
   - Markdown only (runbooks, ADRs, design docs): `references/docs.md`.
   - `.ts`, `.tsx`, `.js` or `.jsx`, or a `<script>` added to a server-rendered template: `references/frontend.md`.
   - Any file `check/classify.py` labelled `generated` (step 0): `references/bundle.md`, in place of `frontend.md` for those files.
   - Backend source with no reference here (Python, Go, PHP, Ruby, Java): read the repo's own `CLAUDE.md`, `CONTRIBUTING` and test setup. They give its conventions and its safe test command. Then apply the steps below.

3. **Attack the frame.**
   - A gap the body files as out of scope or "separate" is still a finding when it sits in a function the PR edits. Ask in a `question` where it is tracked. Only a gap in code the PR neither touches nor reaches goes to chat.
   - Every claim the PR body makes about itself is a hypothesis: "no behaviour change", "fail-closed", "only staging", "known gap", "moved as-is", "review folded in". Check each against the code.
   - A claim someone will act on after merge is checked the same way: a list of expected symptoms, a deploy or rollback step, "safe to ship before X". A wrong expected-symptom list is worse than none, because it tells the operator to ignore a real break. It is at least `should fix`, posted at `PR`.
   - A claim about how the system works ("this is a global scope", "nothing else writes this") gets checked against the repo's rules and memory before you build on it. A wrong one in a docblock or the body is the finding, even when the code around it is harmless.
   - Write the ticket's problem as one sentence: who sees what, where. Criteria written as implementation ("add column X") can all pass while that person still sees it. Trace that exact scenario through the PR head, not an easier one. List every path that can produce the symptom (each client, entry point, import type, job) and say which ones the diff covers. An uncovered path is a finding even when every criterion passes. Check that the PR's test uses the ticket's case as its fixture.
   - Write down the premise the change needs to work at all ("the browser can reach this", "this profile cannot reach prod", "this path resolves where the skill runs"). Then try to break it against the real topology.
   - When the diff adds a guard, check or detector, list the good inputs that look like the bad one to it. Examples are a second instance, a valid empty value, a hidden element, or a valid name the pattern also matches. Ask about the likeliest one as a question, and run it only when you want to state it as fact. A guard that fires on a good input blocks a user who did nothing wrong, and a test of failures alone never shows it.
   - To see a flow the PR changes from trigger to effect, run `../shared/skills/current-state` steps 1 to 3.
   - When the diff adds a new kind of thing (a class family, component type, table, endpoint family or skill), run `../shared/skills/design-options` in JUDGE mode on that addition. A SHAPE line that FAILS from its step 3 or step 5 is a finding, usually a `question` that cites the precedent it should have configured. It is `blocking` only when later work would copy the wrong shape or it is hard to undo. Word it per step 8.

4. **Chase what must stay in sync.** Where the diff changes a signature, return value, stored key or shared state, grep every other reader and writer. Where it writes an entity (a model, table or stored key), `../shared/skills/blast-radius` steps 0 to 5 list its hooks, scopes, writers and readers. Each is a candidate under the grep rule below. Say which were updated. A value written in two places that must agree is a defect when they are not bound together. For the fix, prefer an existing home (check that its value matches the literal, or the swap changes behaviour), then config, then a class constant. Where the PR moves files, diff each old file against its new copy. What changed in transit is where the bugs are. A file copied from another repo can also miss edits that landed there after the copy. Run `python3 "$SKILL_DIR"/check/moved_drift.py <source repo> <ref>:<path> <copy> [--rename OLD=NEW ...]` on each one, with the renames the move applied. When a finding is a pattern, list every site with a grep or script before you draft. Two sites you read are a sample, not the finding. A grep hit is a candidate, not a site. It counts once you have read it, it has the same defect (the same operation, not just the same name), and something can write the value it needs. The count and the command go in its `Sites:` line.

5. **Measure what you will state as fact.** A claim such as "nothing covers X" or "this aborts before Y" needs a run behind it. A finding you can ask as a question needs none. Do not run the suite or sweep mutations by default. Run only what those findings rest on. To prove a test gap, mutate the one piece of logic the finding is about and see whether a test goes red. A mutation that leaves every test green is a gap only when it changes what a user or operator sees, so check that an earlier guard does not mask it. For a script that wraps a CLI, put a stub of that CLI first on `PATH` that logs every call, and run the script. The reference for the file type, or the repo's own docs (`CLAUDE.md`, `CONTRIBUTING`, the test config), names the safe way to run things.

6. **Verify each candidate.** Treat every candidate as false until you have read the thing it rests on.
   - Read from the PR ref (`git show pr-<n>:<path>`), not the working tree.
   - A third-party contract (request shape, status, permissions) needs the provider's doc or the policy file, read now.
   - A claim about what the PR used to do comes only from `git log <base>..pr-<n>` and `git show <sha>:<path>`. Never a local branch, stash, worktree or your own fix commit. Name the sha.
   - A claim about another PR (which files it touches, whether it merged, why it is DNM) is read from that PR now: compare `git diff --name-only` of both, and `gh pr view` for its state.
   - A suggested fix that calls existing code needs that code at the PR head, not only on master: `git grep -n <symbol> pr-<n>`. If it is only on master, the ask includes merging master first.
   - Sub-agents that gather facts (greps, doc lookups) return facts. The judgement of whether the code is right stays with you or a refuter.
   - If `/automate-me:verify-web pr <n>` left a `verify.md` for this PR, check it with `python3 "$SKILL_DIR"/../verify-web/check/check_verify.py <verify.md>` first. Each CONTRADICTED scenario is a finding, at least `should fix`, with its base and head results as `Step: measured` lines. VERIFIED scenarios go in the review body as notes. NOT RUN ones go in the "not verified" line.

7. **Classify.** A line someone else already commented on is taken. Comment there only if you change its severity, its fix, or whether it is real, and then as a `reply <id>` inside their thread. A finding with one taken site and one untouched site is still new at the untouched site. A finding the author already answered is handled unless their answer is wrong. Tag each survivor `blocking`, `should fix`, `question` or `nit`. Check the diff against each acceptance criterion; an unmet one is at least `should fix`. Cut to 5 findings per PR, nits folded into one comment. Cut questions and nits first.

8. **Draft.** Read `../shared/voices/engineer.md`, then write `drafts.md` per `SKILL.md`. Comments are questions, not verdicts. Name the file, line or value; never "this seems risky". For a bug, point at what to measure rather than writing the fix, unless the fix is obvious. When the same pattern needs a different answer at one site, say so on that site's comment.
   - For each `blocking` or `should fix` finding, write its `Step:` lines, trigger first and failure last, each labeled measured or inferred.
   - Anchor only on lines inside a hunk. Get the right-side ranges first; a line outside every hunk rejects the whole review when posted:
     ```
     git diff <base>...pr-<n> -U3 -- <file> | sed -nE 's/^@@ [^+]*\+([0-9]+)(,([0-9]+))? @@.*/\1 \3/p' | awk '{n=($2=="")?1:$2; print $1"-"$1+n-1}'
     ```
     If the line you mean sits between hunks, anchor on the nearest changed line and name the real line in the text, never "here".
   - Link: `<pr url>/files#diff-<hash>R<line>`, with `hash=$(printf '%s' "<path>" | shasum -a 256 | cut -d' ' -f1)`. `echo` adds a newline and gives a dead anchor. If an anchor does not jump, use `https://github.com/<o>/<r>/blob/<head sha>/<path>#L<line>`.
   - Run `check/check_drafts.py` and fix what it flags.

9. **Refute the drafts.** Hand `drafts.md` to one or two fresh sub-agents that have not seen your notes, working from the PR heads, on your strongest-judgement model. For each comment they answer, with quoted evidence:
   1. Sibling. Does the closest existing code already do the same thing? Then say "same as the sibling", or drop it, but drop it only when the refuter measured what the sibling does on this path. A missing test is the exception. Keep a test-gap finding, even when weak tests are the house style, if it names two things. One is a wrong behaviour a user can reach. The other is a test the author can add in the current CI. Reword a general one ("the tests only read source text") into that shape rather than drop it.
   2. Direction. Would the suggested fix work if applied literally, and does it close the whole failure or only narrow it? Reword an ask that only narrows it into the fix that closes it, and name that fix's cost. If it involves a credential or permission, read the policy that grants it. If it says what happens when a flag or variable is absent, read the fallback code. Does another PR or consumer depend on the current behaviour?
   3. Already answered. Does the PR body, a docblock, test, comment or author reply already state it? A gap the body lists as known is answered unless its reasoning is wrong, or it sits in a function the PR edits and no issue tracks it. Answered means you never word it as if the author did not see it. It does not mean you drop the ask. Sometimes the fix is small and gives the same result on the runtime prod runs today. Then keep it as a `question` that names the body's residual and asks to fold it in. Drop it only when the body gives a reason the fix is wrong or unsafe, not just that it was left for later. A "measured" or "unchanged" claim in the body answers nothing until the refuter reruns it.
   4. Numbers. Recompute every count and line number. A step labeled `measured` needs the run behind it. Relabel it `inferred` when there is none.
   5. Still true. Grep each factual claim at the current head, including the claim in each step. Relabel a `measured` step `inferred` when no run backs it.
   6. Reachable. For each site, find what writes the input the finding needs. A site nothing can reach is dropped.
   7. Severity. Run the same scenario on the base. If the base behaves the same, the PR did not cause it, so it is a `question` or a follow-up, never `should fix`. If the failure overwrites or deletes saved data, it is at least `should fix`, even when it needs a failed request first.
   8. Prose. Read the comment and its `Plain:` line aloud, against the `[judgment]` rules in `../shared/writing-rules.md`. Reword any dropped articles or verbs (W11), figurative verbs (W24), missing actor (W10) or stacked hedge (W7). The script checks none of these.

   They return `accurate`, `reword` or `drop` with corrected text. Apply it, rerun the check, and record the totals in the `Refuter:` line only.

10. **Publish.** Run `python3 "$SKILL_DIR"/check/live_state.py <dir>/drafts.md` and act on what it prints. Give a PR it reports closed or merged a `scope:` verdict that says so, and drop its comments. For a moved head, follow the stop rule below. Then render the page with `check/render_page.py` and publish it with the `sample` capability, as `SKILL.md` says. Reply in chat as `SKILL.md` says. Stop.

## Stop rules

- PR not found or closed: stop.
- The head moves during the review: refetch, then redo steps 6 to 9 for the changed files.
- A `blocking` finding that the refuter could not confirm: tag it `question`, not `blocking`.
