---
name: breakdown
description: Break a rough idea or problem into at most 8 small items, each with a spec an agent can run (outcome, done when, limits, harness, loop cap, verifier). Publish one short page with a build-order diagram that a PM or any engineer can read. Then defend the plan one item at a time when the user challenges it. Use for "break this down", "turn this idea into tasks", "mini PRD", "plan this project", or an idea too big for one prompt. For one prompt, use /outcome or brief-check. For a full PRD or EDD, use review-prd or write-edd.
---

# Breakdown

Turns an idea into items an agent can build and prove one at a time. The plan lives in `plan.json`. The page and every agent prompt render from it, so a change made in one place shows up everywhere.

Keep every output short. The page says each thing once in plain words, and detail stays folded. A chat reply never repeats the page.

## Run

1. **Is it one prompt?** If the idea fits one agent run, write its outcome, done-when and limits lines and stop. Say breakdown is not needed.
2. **Read the ask whole.** A colleague's message goes through decode-ask first. For the user's own idea, quote their words as written in `ask.quote`, every message that makes up the ask. If a message points at a reply you can't see, say so in `big_picture` and mark your reading a guess. Then write the project's `outcome`, `done_when` and `limits`, with your best guess where they left one out. Their wording may be wrong; restate what they mean, not what they typed. Read code or docs only to name a part or to check a premise.
3. **Ask at most 2 questions**, and only where a wrong guess would change the items. Each one gets a suggested answer. Otherwise go on.
4. **Split into items.** Each item is one agent run that ends in a check, sized `S` or `M`. Split an `L`. More than 8 items means two projects; say so and plan the first. Put first the item whose result could change the rest of the plan, such as a test of a premise. The page marks it. `after` lists the items that must finish first. Items with nothing in common have nothing in `after`, so they run in parallel. An item needed only on some result of another gets `only_if`, as in "A finds no skills folder." An item waiting on a skipped item treats it as passed.
5. **Write each spec.** Pick the harness from `../shared/harness-kinds.md`. Give the loop a cap and say what the agent reports when it hits the cap. The verifier is a fresh agent that never saw the work. A passing harness is not proof, so the verifier also compares the output with the outcome and tries one case the harness misses. For an item that changes code, an agent that did not write the diff reviews it before the item closes. Name the tools it needs. Pick the model and effort for the job: the smallest model that can do it, with more effort for judgment. `context` lists the only files and outputs the agent gets, so it never inherits the whole chat. An item that answers a question rather than changing code uses the `findings file` harness.
6. **Find the gaps.** Match the idea to the engineer rule sets in shared/rules/eng, when any exist, and `../shared/rules/` (PM questions). List every engineering set in `patterns` as fired or not fired, so a missed match shows on the page. For each fired check the plan does not already answer, add a gap: put its `done_check` into an item's `done_when`, or make it a question. Add a gap from a run or file as `evidence`, and one you predict as `guess`. Drop any gap that changes no item. At most 8 gaps.
7. **Record the decisions.** Each choice a reader could question gets a `decisions` entry. It names the option you rejected and why, with a label: **measured** (you ran or read it), **inferred** or **guess**. A choice whose parts have different labels splits into two entries. These entries are what you defend from later.
8. **Check it.** `$SKILL_DIR` is this skill's directory. Claude Code prints it as "Base directory for this skill" when it loads. In Codex, it is the folder that holds this SKILL.md. Run `python3 "$SKILL_DIR"/check_plan.py <plan.json>` and fix what it flags. It caps the plan at 900 words and 2 open questions in all, the same 2 as step 3, so cut decisions and limits before items. The shape and its limits are in `references/plan-shape.md`.
9. **Cold read.** Run `python3 "$SKILL_DIR"/render_plan.py --text <plan.json> > page.txt`. Give a fresh worker on haiku only that file's path and tell it to read nothing else. Write your own answers first. The reader answers three questions. What gets built? In what order? Which item could change the rest of the plan, and why? Fix the part of the plan behind each wrong answer and each point the reader called unclear. Rerun steps 8 and 9 once if an answer was wrong. If the second read still differs, say so in the reply.
10. **Render and publish.** Run `python3 "$SKILL_DIR"/render_plan.py <plan.json> > page.html`, look at it once in a browser, then publish `page.html` as an artifact, with `plan.json` published beside it through `files`. Never hand-write the page. To change how it looks, change `render_plan.py`.
11. **Reply** with the link, one line on what the plan builds, and the open questions. Nothing else.

## Next rounds

The user names one item or one decision, as in "more on B" or "why is C after B?". Read `plan.json` back from the artifact if it is not in this session.

- Answer that item only, in at most 5 sentences, from its `decisions` entry and the evidence behind it.
- If their point brings a fact the plan lacked, change the item and add a `log` entry with `changed`. If it doesn't, keep the item and add `held` with the evidence. Never change an item only because they pushed back.
- After any change, rerun step 8, render again and publish to the same URL.

## Hand off

`python3 "$SKILL_DIR"/render_plan.py --prompt B <plan.json>` prints item B as an agent prompt with the brief-check slots filled. The user starts each run, or tells you to. Run items in `after` order. Each run ends by updating `RESUME.md`, so a new session picks up from the file, not the chat. An item starts only when every item it waits for has passed its verifier. The agent that did the work never calls it done or correct. It reports what it ran and the output, and only the verifier closes the item.

## Enforced by

- `check_plan.py`: shape, sizes, order, harness kinds, loop caps, decision labels, gaps and the writing rules (step 8).
- A second model: the cold read (step 9).
- The user: the challenges in Next rounds.
