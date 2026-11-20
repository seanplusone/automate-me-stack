---
name: shape-idea
description: Brainstorm a vague idea before outcome. The user wants something and does not yet know how it looks or how it works. Each turn restates the idea, asks one question, and names at most one risk. Decisions go into decisions.md as they are made. It stops when a goal, a done line and one more decision are set, or at 10 turns, or at 5 open items, then hands the file to outcome. It never builds, runs, or posts anything. Use for /shape-idea, "help me think this through", "I have an idea but no plan", or a want with no shape yet.
---

# Shape an idea

The user has a want and no shape for it yet. They can say what they want. They cannot yet say how it works, or what finished looks like. This skill asks one question at a time and writes each decision down. It stops on its own. Then it hands the notes to [outcome](../outcome/SKILL.md). It never fills a gap with a guess.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## When to offer it

The user can type `/automate-me:shape-idea`. A message may be a want with no plan and no picture of done. Then offer it in one line. "Want to shape this before we write a brief?" Without a yes, answer the message as usual. With a yes, start turn 1.

If the message already names the goal, the limits, and what done looks like, offer outcome instead. This skill is the step before that brief.

## What it never does

It writes one file, `decisions.md`, and then stops. It does not build, run, or post. It does not start outcome or any other skill. It does not pick a stack, a library, or a file layout. Those would be guesses.

The steps are the same for any project and any stack. They do not depend on one coding agent. Claude Code, Codex, and others follow this file as written. Agent-specific wiring stays out of the notes.

## 1. Each turn

A turn is one reply. Keep it short. The opening reply is turn 1.

On every turn before a stop:

1. Restate the idea so far in one or two sentences, in your own words.
2. Ask exactly one question. Ask the gap that would change the shape most. Use this order. First the missing goal. Then what done looks like. Then the next firm choice.
3. Push back at most once. Name one risk or one contradiction, in one sentence. If nothing clashes, add nothing.

Then wait. Do not add a second question. Do not list options. Do not sketch a design.

On the turn that hits a stop, restate the idea and stop. Do not ask a question on that turn. You may still name one clash, and then you stop.

A pushback is spoken. It is written down only if the user then decides.

## 2. Write the decision down

Write `decisions.md` in the session's scratch folder. Update that same file. The moment the user decides something, add it before the next question.

Keep the user's own words for every number and name. Never round, convert, or "fix" them. If they said "10 seconds", write "10 seconds". If they said "4am", write "4am".

Read the whole message before you write. Sort each part into one section. Each item is one line.

| Part of the message | Where it goes |
|---|---|
| The firm want | Decided, a line that starts with `goal:` |
| What finished looks like | Decided, a line that starts with `done:` |
| Any other firm choice | Decided, its own line |
| A hedge, or a gap only the user can close | Open, one line that ends in `?` |
| For later, or off the idea | Parked, or `none` |

A hedge is "maybe", "I think", or "not sure". It is not a decision. If a wrong guess would change the shape, it goes to Open. "Later" goes to Parked, even when it is hedged.

A self-correction replaces the line it fixes. "Actually X" or "no wait, X" keeps only the new line.

The file uses these sections, in this order. Copy the labels as they stand.

```
# Decisions: <short title>

## Decided

- goal: <the want, in the user's words for numbers and names>
- done: <what finished looks like>
- <one other firm choice>

## Open

- <the gap, then the one question that settles it?>

## Parked

- <a tangent or a later idea>
- none

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
- map: Decided goes to Goal and Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
```

Handoff is written only on the stop turn. Until then the file has the first three sections.

On a later turn, a firm answer becomes one Decided line. Remove the Open line it settles. If the user moves it to later, put it in Parked and remove it from Open. A later turn adds at most one new Open line, and only when the answer is still a gap.

## 3. Stop

After you save a message, check in this order. The first match wins. Write Handoff and do not take another turn.

1. **done.** Decided has a `goal:` line, a `done:` line, and at least one other line.
2. **open-cap.** Open has 5 items. If the message has more than 5 gaps, keep the 5 that change the shape most. Do not write the rest.
3. **turn-cap.** This reply is turn 10.

Record that turn as `turns: <n>` in Handoff. Never write a turn above 10.

Record the message first, up to those 5 open items. A stop ends further turns. It does not drop lines the user already stated in this message.

## 4. Hand off

A finished file has a Handoff section. A run without one fails the check.

`stop` is one of `done`, `turn-cap`, or `open-cap`. `next` is `/automate-me:outcome`.

Tell the user the next step in one line. They type `/automate-me:outcome` and give it `decisions.md`. Do not run outcome yourself.

Outcome reads the sections like this.

| Section | Lands in the brief as |
|---|---|
| The `goal:` line | Goal |
| Every other Decided line | Must-haves |
| Open | Unknowns |
| Parked | Parking lot |

Run `python3 "$SKILL_DIR"/check/check_decisions.py <decisions.md>` after you write Handoff. Fix what it flags before you show the file. It checks the shape. The four sections are present once, in order. Every Open item ends with `?`. Open has at most 5 items. `stop` is one of the three reasons. `turns` is a whole number no higher than 10. When `stop` is `done`, Decided has a `goal:` line and a `done:` line. No item runs past one line. Handoff names outcome.

The reply follows the [writing rules](../shared/writing-rules.md). The user's words inside `decisions.md` stay as they said them.

## Optional helpers

Nothing here needs pstack. If pstack is installed, `/in-your-own-words` can restate the idea. `/sharpen` can tighten one fuzzy line. Both are optional. Skip them when pstack is absent. The questions and the file stay the same.

## Why

A bare want is easy to over-build. One question at a time keeps the user's answers as the only source for the shape. The caps stop the chat before it turns into a design. The handoff gives outcome a file of decisions instead of a ramble.
