---
name: shape-idea
description: Brainstorm a vague idea before outcome. The user wants something and does not yet know how it looks or how it works. Each turn restates the idea, asks one question, and names at most one risk. Decisions go into decisions.md as they are made. It stops when the five slots are decided, at turn 10, or after turn 1 when more than 5 other gaps stay open. Then it hands the file to outcome. It never builds, runs, or posts anything. Use for /shape-idea, "help me think this through", "I have an idea but no plan", or a want with no shape yet.
---

# Shape an idea

The user has a want and no shape for it yet. They can say what they want. They cannot yet say how it works, or what finished looks like. This skill asks one question at a time and writes each decision down. It stops on its own. Then it hands the notes to [outcome](../outcome/SKILL.md). It never fills a gap with a guess.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## When to offer it

The user can type `/automate-me:shape-idea`. A message may be a want with no plan and no picture of done. Then offer it in one line. "Want to shape this before we write a brief?" Without a yes, answer the message as usual. With a yes, start turn 1.

If the message already decides goal, done, output, verify, and constraints, offer outcome instead. This skill is the step before that brief.

## What it never does

It writes one file, `decisions.md`, and then stops. It does not build, run, or post. It does not start outcome or any other skill. It does not pick a stack, a library, or a file layout. Those would be guesses.

The steps are the same for any project and any stack. They do not depend on one coding agent. Claude Code, Codex, and others follow this file as written. Agent-specific wiring stays out of the notes.

## 1. Each turn

A turn is one reply. Keep it short. The opening reply is turn 1.

On every turn before a stop:

1. Restate the idea so far in one or two sentences, in your own words.
2. Ask exactly one question. Ask a missing slot first, in this order: goal, done, output, verify, then constraints. Then ask the next firm choice.
3. Push back at most once. Name one risk or one contradiction, in one sentence. If nothing clashes, add nothing.

Then wait. Do not add a second question. Do not list options. Do not sketch a design.

On the turn that hits a stop, restate the idea and stop. Do not ask a question on that turn. You may still name one clash, and then you stop.

A pushback is spoken. It is written down only if the user then decides.

## 2. Write the decision down

Write `decisions.md` in the session's scratch folder. Update that same file. The moment the user decides something, add it before the next question.

Keep the user's own words for every number and name. Never round, convert, or "fix" them. If they said "10 seconds", write "10 seconds". If they said "4am", write "4am".

Read the whole message before you write. Sort each part into one section. Each item is one line.

Five slots are required: goal, done, output, verify, and constraints. Each one is a Decided line that starts with its name, or an Open line that starts with its name and ends with one question. A slot the user did not decide is Open. Write a missing slot before any other gap. An example is `output: what comes back, a list or a page?`. A slot line does not count toward the open cap. A gap past that cap goes under Parked, question and all. Do not drop it.

| Part of the message | Where it goes |
|---|---|
| The firm want | Decided, a line that starts with `goal:` |
| What finished looks like | Decided, a line that starts with `done:` |
| What comes back | Decided `output:`, or Open if not chosen |
| How to check it | Decided `verify:`, or Open if not chosen |
| Firm limits | Decided `constraints:`, or Open if not chosen |
| Any other firm choice | Decided, its own line |
| A hedge, or another gap | Open, one line that ends in `?` |
| For later, or off the idea | Parked, or `none` |
| A firm exclusion | Decided `out of scope:`, or Parked tagged `out of scope:` |

An Open line is a question when it ends in a question mark. A mark of any script counts, and closing markup, quotes and brackets after it do not matter. A line with a mark only in the middle is not a question.

A hedge is "maybe", "I think", or "not sure". It is not a decision. If a wrong guess would change the shape, it goes to Open. "Later" goes to Parked, even when it is hedged. A Parked line stays in outcome's Parking lot. Only an `out of scope:` tag makes it an exclusion.

"Unknown" is not a decision either. A slot, or a `tools:`, `agents:`, `evals:` or `decide:` line, that the user calls unknown goes to Open as a question. A Decided line that still holds the word goes on the check's CHECK WITH ME list, described in the handoff step.

A Decided `evals:` line names one case that should pass and one that should fail, as `evals: pass: <case>; fail: <case>` or `evals: <case> should pass, <case> should fail`. A Decided `decide:` line says what the user will decide with the result. It goes to Goal. Without it, outcome's decide question waits in Unknowns. A Decided `out of scope:` line is a firm exclusion.

A self-correction replaces the line it fixes. "Actually X" or "no wait, X" keeps only the new line.

The file uses these sections, in this order. Copy the labels as they stand.

```
# Decisions: <short title>

## Decided

- goal: <the want, in the user's words for numbers and names>
- done: <what finished looks like>
- output: <what comes back>
- verify: <how you will check it>
- constraints: <firm limits>
- <any other firm choice>

## Open

- <a missing slot, as `output: what comes back, a list or a page?`>
- <any other gap, ending with one question?>

## Parked

- <a tangent or a later idea>
- none

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 1
- writing: pass
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
```

A slot lives in Decided or in Open, not in both. Handoff is written only on the stop turn. Until then the file has the first three sections.

On a later turn, a firm answer becomes one Decided line. Remove the Open line it settles. If the user moves it to later, put it in Parked and remove it from Open. A later turn adds at most one new Open line, and only when the answer is still a gap.

## 3. Stop

After you save a message, check in this order. The first match wins. Write Handoff and do not take another turn.

1. **done.** All five slots are Decided lines, and none of them is also Open.
2. **open-cap.** Not on turn 1. After that, Open has more than 5 lines that are not the five slots.
3. **turn-cap.** This reply is turn 10.

The first match is the only legal stop. If done matches, do not write open-cap or turn-cap. If open-cap matches, do not write turn-cap.

Record that turn as `turns: <n>` in Handoff. The number is from 1 through 10.

The five slots do not count toward open-cap. A slot label still counts when a space sits before the colon, or the colon is the full-width one. `Output : still open?` is the output slot.

On turn 1, Open may hold at most 5 lines that are not slots. Park the rest, each with its question. Do not stop on turn 1 for the cap. A parked gap is not dropped. Outcome reads Parked as the Parking lot.

Every part of the user's message lands in Decided, Open, or Parked. A hedge stays Open or Parked. Do not write it as a firm line.

## 4. Hand off

A finished file has a Handoff section. `stop` is the first match from the list above. `next` is `/automate-me:outcome`. The map line in the template is required. Case does not matter.

Before you write Handoff, run the repo's shared writing check. From this skill that script is `../shared/check_writing.py`. Run `python3 "$SKILL_DIR"/../shared/check_writing.py <decisions.md>`. Fix the lines it flags. Do not change the user's numbers or names. If a fix changes a line, run the check again.

If pstack is installed, also run `/unslop` as an extra pass on the file. If it is not installed, skip that pass and continue. Do not require pstack.

When the writing check passes, add `writing: pass` under Handoff.

Tell the user the next step in one line. They type `/automate-me:outcome` and give it `decisions.md`. Do not run outcome yourself.

Outcome reads the sections like this. This skill does not ask Tools, Agents and roles, or Evals, and it does not invent them.

| In the decisions file | In the brief |
|---|---|
| The `goal:` line | Goal |
| The `done:` line | Done |
| A decided `out of scope:` line | Constraints |
| A decided `decide:` line | Goal. Without one, the decide question goes to Unknowns |
| Other Decided lines | Done |
| A decided `output:` line | Output |
| An open slot | That slot as `unknown:`, and again under Unknowns |
| The `constraints:` line | Constraints |
| A Parked line tagged `out of scope:` | Constraints as `out of scope:`, and the Parking lot. A tagged question goes to the Parking lot and Unknowns |
| A Parked question | Unknowns as `unknown: <question>?`, and the Parking lot |
| Other Parked lines | Parking lot |
| The `verify:` line | Verification |
| A decided `tools:`, `agents:`, or `evals:` line | That slot, in the user's words |
| Tools, Agents and roles, and Evals when unset | Unknowns |
| Each yes in `confirmed.md` | The brief's `## Confirmed` block |
| Each new answer in `confirmed.md` | The old value's place |

The read-back asks at most 3 questions, in this order: an open goal or done question, then the decide question, then Tools, then Agents and roles, then Evals. Unasked ones stay in Unknowns.

Run `python3 "$SKILL_DIR"/check/check_decisions.py <decisions.md>` after you write Handoff. It has three outcomes.

- Exit 1, FORMAT INVALID. The file breaks a rule the script knows for certain. Examples are a missing section, a missing Handoff line, a blank slot, a template hole such as `<goal>`, a placeholder such as TBD, or a writing failure. Fix what it flags before you show the file. The checks are listed in `README.md`. A code fence under Decided, Open or Parked fails, because its text would not reach the brief. `writing: pass` does not override a writing failure.
- Exit 2, CHECK WITH ME. The format is valid, and the script found values it cannot be sure about. It prints one list. Each item names the slot and the exact value. Then come Why, Ask, Suggest and Line. Why says in one short sentence why it may not be ready. Ask holds one to three questions that narrow the answer for that slot. Suggest is a suggested answer or next step. Line is the item's `confirmed.md` line, ready to copy.
- Exit 0, PASS. The handoff is ready.

This is the check-with-me step. It is a drill-down. On exit 2, stop and show the user the list, one item at a time. Do not guess the answer. Ask the item's Ask questions until the answer is exact. Then add one line for it to `confirmed.md`, in the same folder as `decisions.md`. Copy the item's `Line:` as it is. After the bar, keep `yes` to keep the value as written, or write the user's new answer in their words in place of `<new answer>`:

```
- Output: maybe a poster on the gym door | yes
- Output: maybe a poster on the gym door | a poster on the gym door
```

A bar inside the value or the new answer is written `\|`, and a backslash `\\`. The `Line:` already writes the value that way. So the one bar with no backslash before it splits the line. A new answer takes the old value's place in the brief, and the line keeps its label. `no` alone is format invalid, so write the new answer in its place. The latest line for the same slot and value wins. Do not edit `decisions.md` for an answer. Then run the check again.

The new answer goes through the same check. If it is still unsure, it is listed again under its new text. Ask again, and add a line for the new text. A yes clears only its own item, the one with that slot and value. No answer clears a format error, a writing failure included, and a yes never clears an Evals line with no pass case and fail case: add the cases. A line that no longer matches any value prints a NOTE. Remove that line.

Every value goes through one shared check, so the same text gets the same answer in every slot. In a Decided value or an `out of scope:` line it lists the word "unknown" anywhere and any question mark. It also lists a hedge such as "maybe" or "not sure", and a trap word such as "clean". Everywhere it lists a hole or an `[insert ...]` inside a longer value, `none`, and a placeholder word inside a longer value. Punctuation does not hide one, so `a card/TBD` and `poster-TBD` are listed. An Open line is a question when it ends in a question mark. A line with a mark only in the middle is listed. A Parked `out of scope:` line with a question mark is listed too. A wrong item costs one answer. A missed one costs a wrong brief.

The reply follows the [writing rules](../shared/writing-rules.md). Inside `decisions.md`, keep the user's numbers and names, and rewrite any line the writing check flags.

## Optional helpers

Nothing here needs pstack. If it is installed, `/in-your-own-words` can restate the idea and `/sharpen` can tighten one fuzzy line. `/unslop` is only the extra pass in the handoff step. Skip any of these when pstack is absent. The questions and the file stay the same.

## Why

A bare want is easy to over-build. One question at a time keeps the user's answers as the only source for the shape. The five slots give outcome a goal, a done line, an output, a check, and the limits. The caps stop the chat before it turns into a design.
