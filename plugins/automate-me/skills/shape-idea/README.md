# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops when the five slots are decided, at turn 10, or after turn 1 when more than 5 other gaps stay open. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Four synthetic scored cases. Each `run-1` was written by a fresh model that read only `SKILL.md` and that case's `input.md`. The input holds the whole conversation. Keys were written from the input, not from the run. habit-tracker, tidy-downloads, and lunch-poll stop at `done`. bookmark-box stops at `open-cap`.

## What the checks cover, and what they don't

`check/check_decisions.py` has three outcomes. Format invalid is only what the script knows for certain. Everything it cannot be sure about goes on one CHECK WITH ME list, so the person decides it. A wrong item costs one yes. A wrong fail blocks a real file.

**Format invalid, exit 1.** It fails when:

- `## Decided`, `## Open`, `## Parked`, or `## Handoff` is missing, repeated, or out of order. Section, slot and field names are ASCII, so `## Decıded` with a dotless i is a missing section, and `wrıting: pass` is a missing writing line. No input crashes the check;
- a slot is missing from both Decided and Open, is repeated, is in both, or is blank (`output:` or `goal: stated:`). A blank slot is also on the CHECK WITH ME list, with a suggestion;
- a value is untouched template text. That is a template hole such as `<goal>`, a template line left unfilled, or a word from outcome's fixed placeholder list such as TBD, TODO or N/A. An Open item that is only a placeholder or a hole (`TBD?`, `<question>?`) fails too;
- a label is left with nothing after it. `decide: stated:`, `tools: stated:`, a lone `stated:` and `out of scope: stated:` fail with a message that names the line;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line is repeated. Bold and a singular label (`**tools:**`, `tool:`, `eval:`) name the same line;
- text sits inside a ``` or ~~~ fence under Decided, Open or Parked, because its text would be lost. An unclosed fence fails;
- `stop` is not `done`, `turn-cap`, or `open-cap`, once, or does not match the file. `stop: done` requires all five Decided and none of them Open. `stop: open-cap` is only after turn 1, and only with more than 5 Open lines that are not slots. `stop: turn-cap` requires `turns: 10`;
- `turns` is not an ASCII whole number from 1 through 10;
- the shared writing check fails on the file, whether or not the line says `writing: pass`;
- an item runs past one line;
- Handoff lacks `next: /automate-me:outcome`, a single `writing: pass` line, or one `map:` line;
- a `confirmed.md` line is not `- <Slot>: <value> | yes`;
- outcome's `check_brief.py` fails the brief the mapper writes.

**CHECK WITH ME, exit 2,** when the format is valid. The triggers are broad and simple on purpose, a word or a character, not a pattern:

- a Decided value, or a Parked `out of scope:` line, with the word "unknown" anywhere (`go-live date: unknown`, `file format (CSV/JSON): unknown`, `the page shows Status: Unknown`);
- any question mark in a Decided value, of any script and inside any markup (`**CSV or JSON?**`, `a Slack message that asks "Who's in for lunch?"`, `勝者だけ、それとも全票？`);
- a hedge such as "maybe", "not sure" or "for now", or a trap word such as "clean" or "good". Also a hole inside a longer value such as `the form submits on <Enter>`, `none`, or a value outcome's brief check would ask about, such as `ok`;
- an Open line with no question mark, or with a hole inside it. Any question mark makes it a question, so `**Should the poll close after 20 minutes?**` passes;
- a Parked `out of scope:` line with a question mark, which may be a limit or a question;
- an Evals line with no pass case and fail case. A yes cannot clear this one. Label the cases.

Each item names the slot as the brief names it, the exact value, a plain reason, and a suggested answer. A real run on `cases/check-with-me/decisions.md` prints:

```
CHECK WITH ME (3)
- Output: "a chat message with the list that asks "Did you water them?""
  Why: It has a question mark, so it may be a question and not a decision.
  Suggest: Move it to Open if it is still a question, or confirm it as is if the answer quotes a question.
- Done: "a plant with an unknown schedule is listed every day"
  Why: It says "unknown", so this may not be decided yet.
  Suggest: Move it to Open as a question, or confirm it as is.
- Tools: "a plain text file of plants, maybe one line each"
  Why: It says "maybe", so the person may not have decided.
  Suggest: Ask for a firm answer and write that, move it to Open as a question, or confirm it as is.
```

The agent shows the list to the person. Each yes goes in `confirmed.md`, next to `decisions.md`, or at the path after `--confirmed`. Blank lines and `#` lines are skipped. Each other line is the slot and the exact value from the list, then ` | yes`:

```
- Output: a chat message with the list that asks "Did you water them?" | yes
```

The agent edits `decisions.md` for any other answer, and runs the check again. A yes clears its item on the next run. It never clears a format error. A yes that matches no value prints a NOTE and does not fail. The mapper copies each yes into the brief's `## Confirmed` block, so the brief check does not ask again. Each confirmed answer is a test case too: `cases/check-with-me/` holds a decisions file, its `confirmed.md`, and `expected.txt`, the list it must print without the confirmations.

**Pass, exit 0,** when the format is valid and every item has a yes. Exit 3 is a usage error: bad arguments, or a path that is missing, a directory, or not UTF-8 text. It prints one line on stderr.

The placeholder list is outcome's, and it is deliberately narrow. A phrase off the list, such as "see notes", passes. The CHECK WITH ME list and outcome's read-back catch the rest.

`check/score_case.py` scores the file against a case key. Terms match loosely, one item at a time. Exit 0 on a full match. Exit 1 on a miss. Exit 2 on a usage error.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the one-sentence or two-sentence restate, the single question, and the single pushback;
- that a pushback is spoken, and written down only after the user decides;
- that numbers and names stay in the user's words;
- that `writing: pass` is written only after the writing check passes. The shape check runs the writing script, and a pass line does not override a failure;
- that a slot sits in Decided or Open, not in both. The check fails when a slot is in both;
- that `/unslop` is skipped when pstack is absent, and is never required;
- that the stop ends the chat, and that nothing is built, run, or posted;
- that the user, not this skill, starts outcome.

## Decisions format

```
# Decisions: <title>

## Decided

- goal: <the want>
- done: <what finished looks like>
- output: <what comes back>
- verify: <how you will check it>
- constraints: <firm limits>
- <any other firm choice>

## Open

- output: what comes back, a list or a page?
- <any other gap, ending with one question?>

## Parked

- <a tangent, or none>

## Handoff

- next: /automate-me:outcome
- stop: done | turn-cap | open-cap
- turns: <n>
- writing: pass
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
```

Outcome reads `goal:` as Goal, `done:` as Done, `output:` as Output, `constraints:` as Constraints, and `verify:` as Verification. Tools, Agents and roles, and Evals stay unknown until the user answers, unless a Decided `tools:`, `agents:` or `evals:` line already fills that slot. An Open `tools:`, `agents:`, `evals:` or `decide:` question takes the place of outcome's stock question for that slot. Open is Unknowns. Parked is the Parking lot. A slot that is still open is an unknown, not a filled slot. A Decided `out of scope:` line goes to Constraints. A Decided `decide:` line goes to Goal. Without one, the decide question goes to Unknowns and the Questions block, not Goal. Each yes in `confirmed.md` goes to the brief's Confirmed block.

## Key format

A key is markdown. Only lines that start with `Decided:`, `Open:`, or `Parked:` are scored. Lines inside code blocks are skipped. Fields are separated by ` | `. The first field names the line. The rest are terms, and every term must sit in one item of that section. A term written `a/b` matches either side. Matching ignores case.

A term matches at the start of a word, so `pet` matches "pets" but not "carpet". A term of 3 letters or fewer must be the whole word, or that word plus s. A term that ends in a digit must end the number, so `10` does not match `100`. A phrase matches across spaces.

## Layout

```
shape-idea/
  README.md                         this file
  SKILL.md                          one question a turn, then hand off to outcome
  check/
    check_decisions.py              the shape check
    score_case.py                   scores decisions.md against a case key
    test_check_decisions.py         python3 check/test_check_decisions.py
    test_check_with_me.py           python3 check/test_check_with_me.py, the three outcomes end to end
    test_score_case.py              python3 check/test_score_case.py
  cases/
    habit-tracker/                  stop: done, turn 3. A phone habit for drinking water.
      input.md                      the ramble, the only thing the skill is given
      key.md                        decided, open, and parked terms
      runs/run-1/decisions.md       following the skill
      runs/score.md                 why it stopped, and the scorer output
    tidy-downloads/                 stop: done, turn 5. A command line tool for a downloads folder.
    lunch-poll/                     stop: done, turn 3. A team bot that picks a lunch spot.
    bookmark-box/                   stop: open-cap, turn 2. A phone box for saving links.
                                    each of the last two: input.md, key.md, runs/run-1/decisions.md, runs/score.md
    check-with-me/                  a saved CHECK WITH ME case. A plant watering list.
      decisions.md                  three values the check cannot be sure about
      confirmed.md                  the person's yes for each
      expected.txt                  the list printed without confirmed.md
```

Nothing here needs pstack. If it is installed, `/in-your-own-words` and `/sharpen` are optional helpers, and `/unslop` is an extra pass after the shared writing check. If it is not installed, skip that pass. The skill runs the same without them.

## Run the checks

From `shape-idea/`:

```
set -euo pipefail
python3 check/test_check_decisions.py
python3 check/test_score_case.py
python3 check/test_judge.py
python3 check/test_break.py
python3 check/test_check_with_me.py
python3 check/check_decisions.py cases/check-with-me/decisions.md
for c in cases/*/; do
  if [ ! -f "$c"key.md ]; then
    continue
  fi
  python3 check/check_decisions.py "$c"runs/run-1/decisions.md
  python3 check/score_case.py "$c"key.md "$c"runs/run-1/decisions.md
done
python3 ../shared/check_writing.py SKILL.md
for c in cases/*/; do
  if [ ! -f "$c"key.md ]; then
    continue
  fi
  python3 ../shared/check_writing.py "$c"runs/run-1/decisions.md
done
python3 ../shared/check_writing.py cases/check-with-me/decisions.md
```

`set -e` stops the loop at the first command that fails. The loops skip `check-with-me`, which has no key and no runs, and check it on its own.

Every `run-1` passes the shape check and the keyword score. The meaning judge is separate:

```
python3 check/judge_case.py cases/<name>/key.md cases/<name>/runs/run-1/decisions.md
```

It runs `codex exec` or `claude -p` when one is on PATH, and prints SKIP and exits 0 when neither is.
