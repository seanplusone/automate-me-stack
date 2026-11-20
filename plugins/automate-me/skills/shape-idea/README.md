# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops when goal, done, output, verify, and constraints are all decided, or at 10 turns, or at 5 open items. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Three synthetic scored cases. Each `run-1` follows `SKILL.md`. habit-tracker and tidy-downloads stop at `open-cap` on turn 1. lunch-poll stops at `done` on turn 3.

## What the checks cover, and what they don't

`check/check_decisions.py` checks a finished file's shape:

- `## Decided`, `## Open`, `## Parked`, and `## Handoff` are present once, in that order;
- every Open item ends with `?` (a lone `none` means the section is empty);
- Open has at most 5 items;
- `stop` is `done`, `turn-cap`, or `open-cap`, once;
- `turns` is one whole number from 0 through 10;
- each of goal, done, output, verify, and constraints starts a Decided line or an Open line;
- when `stop` is `done`, all five of those slots are Decided lines;
- no item runs past one line;
- Handoff has `next: /automate-me:outcome` and a single `writing: pass` line.

Exit 0 when every check passed. Exit 1 when any check failed. Exit 2 on a usage error.

`check/score_case.py` scores the file against a case key. Terms match loosely, one item at a time. Exit 0 on a full match. Exit 1 on a miss. Exit 2 on a usage error.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the one-sentence or two-sentence restate, the single question, and the single pushback;
- that a pushback is spoken, and written down only after the user decides;
- that numbers and names stay in the user's words;
- that `writing: pass` is true, because the shape check does not run the writing script;
- that a slot sits in Decided or Open, not in both (the check passes either way);
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
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints, done, and every other Decided line go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
```

Outcome reads `goal:` as Goal, `output:` as Output, and `verify:` as Verify. The `constraints:` line, the `done:` line, and every other Decided line are must-haves. Open is Unknowns. Parked is the Parking lot. A slot that is still open is an Unknown, not a must-have.

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
    test_score_case.py              python3 check/test_score_case.py
  cases/
    habit-tracker/                  stop: open-cap, turn 1. A phone habit for drinking water.
      input.md                      the ramble, the only thing the skill is given
      key.md                        decided, open, and parked terms
      runs/run-1/decisions.md       following the skill
      runs/score.md                 why it stopped, and the scorer output
    tidy-downloads/                 stop: open-cap, turn 1. A command line tool for a downloads folder.
    lunch-poll/                     stop: done, turn 3. A team bot that picks a lunch spot.
                                    each of the last two: input.md, key.md, runs/run-1/decisions.md, runs/score.md
```

Nothing here needs pstack. If it is installed, `/in-your-own-words` and `/sharpen` are optional helpers, and `/unslop` is an extra pass after the shared writing check. If it is not installed, skip that pass. The skill runs the same without them.

## Run the checks

From `shape-idea/`:

```
python3 check/test_check_decisions.py
python3 check/test_score_case.py
for c in cases/*/; do
  python3 check/check_decisions.py "$c"runs/run-1/decisions.md | tail -1
  python3 check/score_case.py "$c"key.md "$c"runs/run-1/decisions.md | tail -1
done
python3 ../shared/check_writing.py SKILL.md
for c in cases/*/; do
  python3 ../shared/check_writing.py "$c"runs/run-1/decisions.md | tail -1
done
```

Every `run-1` passes the shape check and the score.
