---
name: decode-ask
description: Turn a colleague's message (a PR or Notion comment, a Slack ask, a review note) into one short page before anything runs. The page shows what they want decided, each claim in system terms, and each proposal. It also shows each test with the result that would change our answer. Use when a message asks the user to "run a few quick tests", "take a look", "can we", or mixes claims with a request. Also use for a review with many inline comments on our own doc or PR, and for "understand every claim <name> made". Also use for a pointer such as "I left a comment there", "read this comment" or "see my reply on", even in the middle of another task. Use it before spawning agents or spikes for such a message.
---

# Decode the ask

A colleague's message often holds more than its request. "Run 3 quick tests" can arrive with three claims and a design proposal in the same comment. Running the tests first means the claims and the proposal surface later as fresh confusion, one at a time. This skill pulls them apart before anything runs, so the user agrees on what is being answered.

Nothing runs before the user's go on the page. After it, tests run one per turn (step 4).

## 1. Find the real message, then read it whole

The message the user pastes is often a pointer, such as a Slack line saying "I left a comment there". Find the thing it points at and read that in full, with Notion, GitHub or Slack tools, read only. Also find the question the user asked that started the thread, and quote it. The ask only makes sense as an answer to that question. If the pointer's target can't be found, stop and ask the user for a link. If the colleague opened the thread, there is no question from the user; say so and go on.

On GitHub, inline review comments come from `gh api --paginate repos/<owner>/<repo>/pulls/<n>/comments`. `issues/<n>/comments` returns only the conversation tab.

On Notion, the page id is the last 32 hex characters of the URL. Fetch its comments with all blocks included, or comments anchored to text won't show and the page will look empty.

Mark each premise in the user's question as seen, with the run or file behind it, or as assumed. An assumed premise is a claim, and it gets a test like any other. The colleague's reply is often correcting one.

Quote the real message in full. Read its links if they decide what a claim means. Don't read the codebase yet, except to name a system part (a table, a job, a field) that a claim is about.

## 2. Sort every sentence into one of five kinds

| Kind | What it is | Example shape |
|---|---|---|
| Decision | What they want settled | "should we extend P0-6 instead of building X?" |
| Claim | A statement about how something behaves today | "a reload swaps structures onto other features" |
| Proposal | A design they suggest | "stop if 10% moved more than 1 m" |
| Test | Something they ask us to run | "truncate + append in the test account" |
| Aside | Context that changes nothing | a doc link that backs a claim |

A claim that is true of production today, whatever the doc says (e.g. any signed-in user can delete a record), leaves the page. It becomes its own action item in the reply to the user, with an offer to fix it now.

A proposal is never a test. It gets judged against the claims after the tests, and it may need its own test, which the page names as extra scope.

## 3. Write the page

One artifact page. The user reads the first screen only, and a long page stops them thinking. So the first screen is short, and everything else sits folded below it.

With many items (a review with many comments), group them by subject. Open each group with a short primer that sets up one running example (orders A, B and C), and let the items refer back to it. Each item opens with one plain line and its verdict (writing rule W25), with the story, the quote and the evidence folded below.

Use system terms (record, field, ID number, structure, sync, link). A domain word appears only as a bracketed example, as in "a record (e.g. an invoice)".

**The first screen, at most 150 words and one picture:**

1. **What they want decided.** One sentence. If they never say it, write the one you infer and mark it inferred.
2. **What we'll run.** One line per test. Say what we would do differently for each result, not what the result shows. A test whose results all lead to the same action is left off. Add a line marked "extra" for each proposal that needs its own test, and for each untested claim the decision rests on. A colleague's statement about how a vendor behaves ("the external CRM blocks overwrite once sync is on") counts as untested until we run it.
3. **Ask to the user.** Which test runs first, with a suggestion.

**Folded below, in one `<details>` per section, closed:**

4. **Each claim.** Plain words and which test proves or breaks it. A claim with no test is marked "not tested, taken from <source>". If the decision depends on that claim, name a test for it as extra scope.
5. **Each proposal.** Marked as a proposal. Name the claim it depends on, and whether answering needs a test they didn't ask for.
6. **Fix options.** A claim we agree with, or a proposal that asks for a change, gets two or three ways to act on it. One is marked recommended, or none until the tests are in when no evidence supports a pick. Each option gives what changes, the risk (what goes wrong, and for whom), a size, and its harness from `../shared/harness-kinds.md`. The harness is the test, count or run that fails on today's code and passes after. Each option also lists the steps an agent runs, ending with an independent verifier. An option that reopens one of the user's decisions says so in its risk and names the new fact. Each option has a "Pick this" button. It saves the choice to the page's `db` capability (collection `picks`, one document per item), so the next turn reads the user's picks with `ArtifactData` instead of asking. Load the artifact-capabilities skill before writing the button, and declare the `db` capability when publishing, or the save fails. Before the page goes out, an agent that did not write them checks every one-line summary and every recommended option against the evidence. Anything not checked is labeled "unchecked" on the page.
7. **Each test in full.** Steps, where it runs, what is created and deleted, the expected result, and "If it comes out X, we do Y. If it comes out Z, we do W." A test whose results all lead to the same action is dropped, with that reason. If a test uses a stand-in for a real object (e.g. a hidden note in place of an invoice), name it as a stand-in. Say what it can't prove and what the user will open to check it. A claim about what users see in the app uses the real object.
8. **Their message and the user's question,** quoted in full.
9. **Out of scope.** What we will not run or touch. Name any test another session already ran, with its file, so it isn't repeated.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. Before showing the page, run `python3 "$SKILL_DIR"/check_page.py <page.html>`. It fails when the visible first screen runs over 150 words. Save the page's plain text to a file and run `python3 "$SKILL_DIR"/../shared/check_writing.py <file>`, then rewrite only the lines it flags. Then give the page's plain text to a fresh small-model reader as a cold read, and fix what it restates wrong. The cold read is a filter, not the user's approval.

Publish the page's source data (the item JSON) with the artifact through `files`, so a later session can read it back and edit it. Session scratch is gone next session.

## 4. Run one test per turn, after the user says go

Each result comes back on the same page as:
- the steps done
- what happened, in system terms
- one saved output line the user can check himself, with its file

Never return all the results at once. Never hand a subagent the whole message to "figure out". Brief it with one test from the page. A subagent that drafts page text returns two fields: a plain line in system terms with no IDs, and the evidence (file:line, run, measured or inferred). A subagent that judges a claim gets a neutral brief. It states the doc's own reasoning first, then asks which side the code and the runs support. It never asks "is the reviewer right?". Every premise in the brief names its source (a run or a file and line), or says "verify first".

## 5. Close the loop

When every test is in, add a section that answers the decision in one sentence. Then the user says the answer back in their own words. Draft nothing until they have.

Below it, draft the reply in the colleague's thread, ready to paste. Every line of the reply points at a test result on the page. A line with no result behind it comes out of the reply.

- A line that rejects their proposal needs the same test run against our own design. A simulation is called a simulation, never "tested".
- When the colleague is an engineer, read the write-for-engineer SKILL.md and draft to it, including its writing check.
- After any edit, re-read the reply line by line against the results, and check that no two lines contradict each other. Then search every doc built from the same results (a design doc, a ticket) and fix the same finding there.

## Why

A "3 quick tests" request once took a full day. The tests were one script run. The rest of the day went to claims and a proposal that surfaced after the results, and to redoing a results dump the user could not check. The reply then went out before the user could explain it, and one of its lines contradicted another.
