---
name: review-pr
description: Review one or more pull requests and draft short inline comments plus a verdict, for the user to read before anything is posted. Use for a PR link or number, "review this PR", a set of linked PRs, or a review that will end up as GitHub comments. Works on any repo; repo-specific risk checks load from references/.
---

# PR review

The orchestrator. It runs the playbook and reports back. The output is a short page of comments someone can paste, not a write-up of the review.

A good review is a few findings that are all true, that the author does not already know, each on the line it concerns. Every extra or wrong comment spends the author's trust on the real ones.

## Run

1. Open `playbooks/review-a-pr.md`. Copy its steps into the todolist word for word. With no todolist tool, keep the list in your notes and mark each step as you go.
2. Follow the steps. Each one names the reference, sub-skill or script it uses.
3. Report back in the format below. Nothing else.

## The drafts file

Write `drafts.md` in exactly this shape, in `<scratchpad or $TMPDIR>/review-pr-<n>/`. Never in the repo under review, which other sessions share, or in this skill's directory, which is the plugin cache. It is the only thing the person reads besides the chat reply, and `check/check_drafts.py` checks it.

```
# PR review: <topic in a few words>

<One or two sentences. The main risk across the PRs, in plain words.>

## <owner>/<repo>#<n> | <verdict>
About: <one sentence: what the PR does, for someone who has not read it>
Changes: <the line check/classify.py printed, after the colon>

### <tag> | <path>:<line> | <link to the line>[ | reply <comment id>]
<The comment, word for word as it would be posted.>
Plain: <what the finding means and why it matters, for the user, never posted>
Evidence: <one line: what was read or measured>
Step: measured | <trigger, first step of the flow>
Step: inferred | <next step, ending at the failure>
Sites: <n> | <the command that lists them>

### ...

Body: <one line for the PR description, if any>

## Totals
Refuter: checked <n>, reworded <n>, dropped <n>.
```

Rules for the file:

- **Tags.** `blocking`, `should fix`, `question`, `nit`.
- **Reply.** A finding that sharpens another reviewer's thread ends its heading with `| reply <their comment id>`. It is posted inside their thread, never as a new one.
- **Verdict.** `approve`, `approve after <one thing>`, `needs answer: <the question>`, `hold: <reason>`, or `scope: <what was checked>` for a linked PR read only where it meets the main one. Judge each linked PR on its own code: a wrong one gets `hold:` and a right one gets `approve`. Merge order between linked PRs goes in the review body ("merge after <link>") and never changes the verdict. Use `needs answer:` when the verdict depends on an answer only the author or product owner can give, such as `needs answer: should a read-only admin open events?`. It is not an approval and not a defect. A question that a code change answers stays a `question` finding. Use `approve after` only when the author has one thing left to do. Approve when nothing is serious and the work is in good faith. Judge "serious" by blast radius, not by how much you found. Only a `blocking` finding holds a PR, and a `blocking` finding always does. The check enforces both. Start a `hold:` reason with a verb about the PR ("conflicts with ...", "drops ..."); the page reads it as "Held because it <reason>". A PR that would carry an unapproved or DNM PR into its base is `blocking`, even when it currently cannot merge.
- **Comment.** At most 50 words. A plain fact, then a direct ask. The ask is usually a question, and can be a plain statement of what needs changing.
- **Links.** Every PR, issue, commit or comment a comment names is a markdown link to it: `[acme/orders-api#123](<url>)`, `[abc1234](<commit url>)`. GitHub links a bare `#123` to that number in the PR's own repo, and a bare sha or `repo#n` to nothing. A link counts as one word. The check enforces it.
- **Voice.** Write it in the engineer voice from `../shared/voices/engineer.md`, and read that file before drafting. One plain fact, then a direct ask that names the fix. No pleasantries and no softeners, and no process words from this file (tags, "verdict", "good faith").
- **Review body.** Empty when the PR is approved with no comments. When it is approved with comments, one sentence says the approval stands and the comments are inline, such as "Approving, since an existing order's refund still goes through. The inline comment on the retry warning can be a follow-up." The check enforces it. One more sentence only when something has no line to sit on, such as a stale PR description.
- **PR-level comment.** A finding about code the diff does not touch but the change still reaches, or about a claim in the PR body, has no line to anchor on. Write `PR` in place of `<path>:<line>` and the PR URL as the link. It is posted as a PR comment and counts toward the cap like any other.
- **Page colors.** The badge and tab dot follow the verdict: red for `hold`, yellow for `approve` with comments, `approve after` or `needs answer`, green for `approve` with none, grey for `scope`.
- **Evidence.** At most 25 words, one line. Leave it out when the comment already names its proof.
- **At most 5 findings per PR, and at most 1 nit.** Fold every nit into that one comment.
- **Steps.** `Step: measured | <text>` or `Step: inferred | <text>`, in flow order from trigger to failure. Required on `blocking` and `should fix` (2 to 6, first copy only), optional on `question` (2 to 6), none on `nit`. `measured` means you ran something and saw it, such as a command, a test or a grep count. `inferred` means you read it from code and reasoned. At most 20 words each. They are never posted.
- **Sites.** A finding that is a pattern (the same mistake at more than one place) gets a `Sites:` line. It holds the count of every place it occurs, found by a command, and the command itself. Comment on the sites that matter most and let the count carry the rest. Never stop at the first two you happened to read.
- **One comment per site.** A pattern found at three lines is three comments with the same text. They count once toward the cap. `Plain`, `Evidence` and `Sites` go on the first copy only.
- **Plain.** One line per finding, on the first copy, at most 110 words. Say what the code does wrong and what a user or operator would notice, as you would to a colleague who has not read the diff. Define every term the comment uses that is not plain English (a flag, "post-action", "N+1", "DNM", "rebase").
- **About.** One sentence per PR, what it does in product terms.
- **Changes.** One line per PR, pasted from `check/classify.py` (playbook step 0), such as `12 files: 3 source, 1 test, 8 generated`. When `classes.json` sits next to `drafts.md`, the check fails a missing or edited line, and any finding anchored on a `generated` file. Without it, the check fails an anchor on a hashed or `.gz` file name only. The page shows it under About. It is never posted.
- **Refuter.** `checked` counts distinct comment texts, the review body included.
- Nothing else goes in the file. No "what" and "why" sections, no per-finding refuter notes, no acceptance-criteria table, no skill notes.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. Run `python3 "$SKILL_DIR"/check/classify.py <owner/repo#n> ... --out <dir>/classes.json` first (playbook step 0), and `python3 "$SKILL_DIR"/check/live_state.py <dir>/drafts.md` before publishing (step 10). Load `../shared/writing-rules.md` before writing. Then run:

```
python3 "$SKILL_DIR"/check/check_drafts.py <dir>/drafts.md
```

Rewrite only what it flags. It enforces the caps above and the `[script]` writing rules.

## The page

Never hand-write the page. Render it from the checked file, then publish it with the `sample` capability so its Ask Claude boxes work:

```
python3 "$SKILL_DIR"/check/render_page.py <dir>/drafts.md > <dir>/page.html
```

Publish `<dir>/page.html` with `capabilities: {"sample": {}}`. To change how pages look, change `render_page.py`, not one page. It already does what a reader needs:
- a summary message box with a rich-text Copy button, ready to paste into chat;
- with more than one PR, an overview and one tab per PR, so each review reads on its own;
- plain words before the comment;
- a collapsed Explain panel with a flowchart of the steps, measured solid and inferred dashed, and the same steps as a list;
- code spans instead of backticks, while Copy still gives the GitHub text;
- one card per comment text, listing every line it goes on;
- a short badge, with the verdict's reason as a sentence under it;
- the evidence and Refuter line folded away.

## Reply in chat

At most 6 lines:

1. The single most important finding, in one sentence.
2. The page link.
3. Anything only the user can answer, such as a ticket question addressed to them.
4. What was not verified, in one sentence.
5. The size verdict and its numbers, only when the size check says split.

Write it to W17 to W19 in `../shared/writing-rules.md`: who it affects first, every claim labeled measured, inferred or a guess, and nothing on this list dropped. W2 applies too, so no colon joins two halves of a sentence.

Add one line on the ticket. Say whether the problem is solved (yes, partly or no, naming any path left). Name the criteria source you used (ticket, parent scope, or PR body), and any criterion not met. With no ticket, say the PR was graded against its own claims. Agreement with other reviewers gets a line only when it changes the verdict.

## Posting (only when told)

Never part of the review. Post only when the user says to post, and post the wording they approved, not the first draft.

- "Post it" or "update my review" submits each review with the event its verdict names: `approve` is APPROVE, `hold:` is REQUEST_CHANGES, `approve after`, `needs answer:` and `scope:` are COMMENT. "Stage it" or "leave it pending" posts with no event, so they submit it themselves.
- Use the script, not hand-built payloads. Run it without `--submit` first and read what it prints:
  ```
  python3 "$SKILL_DIR"/check/post_review.py <dir>/drafts.md
  python3 "$SKILL_DIR"/check/post_review.py <dir>/drafts.md --submit --reviewer <their login>
  ```
  It adds them as a requested reviewer where they are missing and posts at each PR's current head. It posts `reply <id>` findings into their threads, and prints each review URL with how many inline comments landed. Give them those URLs.
- After posting, point them to the *Summary message* box at the top of the review page. Its Copy button puts rich text on the clipboard. Pasted into a chat tool such as Slack or Teams, the headings stay bold and each PR number stays a link. Text pasted from the terminal stays raw, so never hand them the message in chat. The box lists each PR as a linked number under Approved, Approved with comments, Needs an answer or Changes requested, and leaves out empty groups and `scope:` PRs. A `needs answer:` PR gets its own group and the box lists its question. An `approve after` PR goes under Changes requested, since it is not approved yet. They post it themselves. `check/summary.py` prints the same message as Markdown, or with `--format slack` in Slack's mrkdwn, for posting through an API.
- Run `python3 "$SKILL_DIR"/check/live_state.py <dir>/drafts.md` first. It fails on a closed or merged PR and on a head that moved since the review.
- Re-check the anchors if a head moved since the review. One line outside every hunk rejects the whole review.
- For a pending review, drop `--submit` and post its payload with no `event` by hand. A `reply <id>` finding cannot go in a pending review; post it after they submit.

## Guards

- Never post, approve, or write to the ticket tracker without a separate instruction.
- Sub-agents get file paths, not pasted text. Read what they return, not their summary.
- A step skipped stays in the todolist as `skip: <reason>`.
