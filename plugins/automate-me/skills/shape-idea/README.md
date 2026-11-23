# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops when the five slots are decided, at turn 10, or after turn 1 when more than 5 other gaps stay open. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Four synthetic scored cases. Each `run-1` was written by a fresh model that read only `SKILL.md` and that case's `input.md`. The input holds the whole conversation. Keys were written from the input, not from the run. habit-tracker, tidy-downloads, and lunch-poll stop at `done`. bookmark-box stops at `open-cap`.

## What the checks cover, and what they don't

`check/check_decisions.py` has three outcomes. Format invalid is only what the script knows for certain. Everything it cannot be sure about goes on one CHECK WITH ME list, so the person decides it. A wrong item costs one yes. A wrong fail blocks a real file.

**Format invalid, exit 1.** It fails when:

- `## Decided`, `## Open`, `## Parked`, or `## Handoff` is missing, repeated, or out of order. Section, slot and field names are ASCII, so `## Decıded` with a dotless i is a missing section, and `wrıting: pass` is a missing writing line. No input crashes the check;
- a slot is missing from both Decided and Open, is repeated, is in both, or is blank (`output:` or `goal: stated:`). A blank slot is also on the CHECK WITH ME list, with a suggestion;
- a value is untouched template text. That is a template hole such as `<goal>`, a template line left unfilled, or only words from outcome's fixed placeholder list such as TBD, TODO or N/A. An Open item that is only a placeholder or a hole (`TBD?`, `<question>?`) fails too. A placeholder word or an `[insert ...]` inside a longer value is not untouched. It goes on the CHECK WITH ME list;
- a label is left with nothing after it. `decide: stated:`, `tools: stated:`, a lone `stated:` and `out of scope: stated:` fail with a message that names the line;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line is repeated. Bold and a singular label (`**tools:**`, `tool:`, `eval:`) name the same line;
- text sits inside a ``` or ~~~ fence under Decided, Open or Parked, because its text would be lost. An unclosed fence fails;
- `stop` is not `done`, `turn-cap`, or `open-cap`, once, or does not match the file. `stop: done` requires all five Decided and none of them Open. `stop: open-cap` is only after turn 1, and only with more than 5 Open lines that are not slots. `stop: turn-cap` requires `turns: 10`;
- `turns` is not an ASCII whole number from 1 through 10;
- the shared writing check fails on the file, whether or not the line says `writing: pass`;
- an item runs past one line;
- Handoff lacks `next: /automate-me:outcome`, a single `writing: pass` line, or one `map:` line;
- a `confirmed.md` line is not `- <Slot>: <value> | <answer>`, or its answer is `no` alone, or a new answer is untouched template text;
- outcome's `check_brief.py` fails the brief the mapper writes.

**CHECK WITH ME, exit 2,** when the format is valid. The triggers are broad and simple on purpose, a word or a character, not a pattern.

**One shared check.** Every value goes through one function, `judge_value(slot, text)` in `check/check_decisions.py`. That covers a Decided slot, a `tools:`, `agents:`, `evals:`, `decide:` or `write first:` line, any other Decided line, an `out of scope:` line, an Open line and a Parked line. The code for one slot only finds the value and picks the wording, so a fix to the check reaches every slot. The same text gets the same answer wherever it sits. `check/test_shared_check.py` checks that over a fixed, seeded set of tricky values. The check reads a value in three layers:

- Text checks apply everywhere. They catch a blank value and untouched template text, which are format invalid. They list `none`, a word from outcome's placeholder list inside a longer value, an `[insert ...]` or a hole inside a longer value, and a value that is too short or vague. A placeholder word counts even when punctuation joins it to a word, as in `a card/TBD`, `poster-TBD` or `flyer,TBD`. The list's everyday words (none, later, pending, placeholder) count only alone. A code span is the person's literal text, so `` `N/A` `` is listed, not format invalid.
- Decision checks apply to a Decided value and to an `out of scope:` line. They list the word "unknown" anywhere (`go-live date: unknown`, `the page shows Status: Unknown`). They list any question mark, of any script and inside any markup (`**CSV or JSON?**`, `勝者だけ、それとも全票？`). They list a hedge such as "maybe", "not sure" or "for now", and a trap word such as "clean" or "good".
- The question check applies to an Open line. An Open line is a question when it ends in a question mark of any script, once closing markup, quotes and brackets go. So `**Should the poll close after 20 minutes?**` passes, and `Should the sale close at noon? Ask on Friday.` is listed.

A Parked line is for later, so only the text checks apply there. A Parked `out of scope:` line with a question mark may be a limit or a question, so it is listed. A value with cases is read in pieces, the way outcome's brief check reads an Evals line. Outside Evals it is read whole as well. The pieces are the text before the first label, and each case body in either form (`pass: …; fail: …` or `… should pass, … should fail`). So `pass: OK; fail: a blank form` is listed in every slot, because `OK` alone is very short, and the brief check asks about it under Evals. In Evals, when the pass case or the fail case is missing, that is the one item for the line, and a yes cannot clear it. Add the cases.

**Format and decisions stay apart.** Only the script decides a format error, and no answer clears one. Only the person clears an item on the list.

**The drill-down.** Each item names the slot as the brief names it and the exact value. Then come four lines. Why is one short, plain sentence that quotes at most a short piece of the value. Ask holds one to three questions for that slot that narrow the answer toward an exact spec. Suggest is a next step, and it offers "confirm it as is" only when a yes can clear the item. Line is the item's `confirmed.md` line, ready to copy, with `yes` or `<new answer>` after the bar. A value with a format error has no Line, because no answer clears it. A real run on `cases/check-with-me/decisions.md` prints:

```
CHECK WITH ME (3)
- Output: "a chat message with the list that asks "Did you water them?""
  Why: It has a question mark, so it may be a question and not a decision.
  Ask: Who will see it, and where? What exactly should it show? How will you know it looks right?
  Suggest: Move it to Open if it is still a question, or confirm it as is if the answer quotes a question.
  Line: - Output: a chat message with the list that asks "Did you water them?" | yes
- Done: "a plant with an unknown schedule is listed every day"
  Why: It says "unknown", so this may not be decided yet.
  Ask: What will you see when it is done?
  Suggest: Move it to Open as a question, or confirm it as is.
  Line: - Done: a plant with an unknown schedule is listed every day | yes
- Tools: "a plain text file of plants, maybe one line each"
  Why: It says "maybe", so the person may not have decided.
  Ask: Which tool or app should it use? What must be ready before it starts?
  Suggest: Ask for a firm answer and write that, move it to Open as a question, or confirm it as is.
  Line: - Tools: a plain text file of plants, maybe one line each | yes
```

**confirmed.md.** The agent asks the person about each item and writes each answer in `confirmed.md`, next to `decisions.md`, or at the path after `--confirmed`. Blank lines and `#` lines are skipped. Each other line is the slot and the exact value from the list, a bar, then the answer:

```
- Output: a chat message with the list that asks "Did you water them?" | yes
- Tools: a plain text file of plants, maybe one line each | a plain text file of plants, one line each
```

- `yes` keeps the value as written. It clears that one item, the one with that slot and value. `tools: Use the terminal` and `agents: Use the terminal` are two items.
- Any other answer is a new answer. It takes the old value's place in the mapped brief. The line keeps its label, once, so an `out of scope:` line stays a limit and an Open `decide:` line stays the decide question. An answer that repeats the label, as `Output:A poster`, is written `output: A poster`.
- A bar inside the value or the new answer is written `\|`, and a backslash `\\`. So the one unescaped bar ends the value, and a line with two such bars is format invalid. In `\\|` the bar is unescaped, because `\\` is one backslash. Each item's `Line:` is its confirmed.md line with the value already written this way, ready to copy.
- `no` alone is format invalid. Write the new answer in its place.
- The latest line for the same slot and value wins.
- The new answer goes through the same shared check. An answer that is still unsure is listed again under its new text, and it needs its own line. Answers apply in the order of their lines in confirmed.md, so that line comes after the one that made the new text. The order of the lines in `decisions.md` does not change the result. Each new answer is checked in its place, as the whole line it becomes, so a later answer never clears an error an earlier one brought in.
- A new answer that is only a placeholder is format invalid. No answer clears a format error. The check reads `decisions.md` as written, before any new answer goes in, so a writing failure stays one too. A line that names a value with a format error prints a NOTE that says so.
- A line that matches nothing prints a NOTE and does not fail. Remove it.

`decisions.md` itself is not changed. The mapper maps it with each new answer in place. It copies each yes into the brief's `## Confirmed` block, once per case body for Evals, so the brief check does not ask again. A `## Confirmed` line cannot clear a fail in the brief check. So the mapper writes a confirmed `[insert ...]` in a code span, and puts `stated: ` before an Evals case such as `` `N/A` ``. The brief check reads both as the person's words. Each saved answer is a test case too: `cases/check-with-me/` holds a decisions file, its `confirmed.md`, and `expected.txt`, the list it must print without the answers.

**Pass, exit 0,** when the format is valid and every item has an answer that clears it. Exit 3 is a usage error: bad arguments, or a path that is missing, a directory, or not UTF-8 text. It prints one line on stderr. Files are read and written as UTF-8, and output is UTF-8, under any locale.

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

Outcome reads `goal:` as Goal, `done:` as Done, `output:` as Output, `constraints:` as Constraints, and `verify:` as Verification. Tools, Agents and roles, and Evals stay unknown until the user answers, unless a Decided `tools:`, `agents:` or `evals:` line already fills that slot. An Open `tools:`, `agents:`, `evals:` or `decide:` question takes the place of outcome's stock question for that slot. Open is Unknowns. Parked is the Parking lot. A slot that is still open is an unknown, not a filled slot. A Decided `out of scope:` line goes to Constraints. A Decided `decide:` line goes to Goal. Without one, the decide question goes to Unknowns and the Questions block, not Goal. Each yes in `confirmed.md` goes to the brief's Confirmed block. Each new answer in `confirmed.md` takes the old value's place.

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
    test_shared_check.py            python3 check/test_shared_check.py, one shared check for every slot
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
      confirmed.md                  the person's answer for each, a yes or a new answer
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
python3 check/test_shared_check.py
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
