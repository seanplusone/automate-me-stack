# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops at a goal, a done line and one more decision, or at 10 turns, or at 5 open items. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Three synthetic scored cases. Each `run-1` was produced by following `SKILL.md` on that case's `input.md`. The opening message already hit a stop, so each file is turn 1.

## What the checks cover, and what they don't

`check/check_decisions.py` checks a finished file's shape:

- `## Decided`, `## Open`, `## Parked`, and `## Handoff` are present once, in that order;
- every Open item ends with `?` (a lone `none` means the section is empty);
- Open has at most 5 items;
- `stop` is `done`, `turn-cap`, or `open-cap`, once;
- `turns` is one whole number from 0 through 10;
- when `stop` is `done`, Decided has a line starting `goal:` and a line starting `done:`;
- no item runs past one line;
- Handoff has `next: /automate-me:outcome`.

Exit 0 when every check passed. Exit 1 when any check failed. Exit 2 on a usage error.

`check/score_case.py` scores the file against a case key. Terms match loosely, one item at a time. Exit 0 on a full match. Exit 1 on a miss. Exit 2 on a usage error.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the one-sentence or two-sentence restate, the single question, and the single pushback;
- that a pushback is spoken, and written down only after the user decides;
- that numbers and names stay in the user's words;
- that `stop: done` also has one Decided line besides `goal:` and `done:`;
- that the stop ends the chat, and that nothing is built, run, or posted;
- that the user, not this skill, starts outcome.

A file can pass the shape check with `stop: done` and no third decision. The skill still forbids that stop until the third line exists.

## Decisions format

```
# Decisions: <title>

## Decided

- goal: <the want>
- done: <what finished looks like>
- <one other firm choice>

## Open

- <the gap, then the one question that settles it?>

## Parked

- <a tangent, or none>

## Handoff

- next: /automate-me:outcome
- stop: done | turn-cap | open-cap
- turns: <n>
- map: Decided goes to Goal and Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
```

Outcome reads `goal:` as Goal, every other Decided line as a must-have, Open as Unknowns, and Parked as the Parking lot.

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
    habit-tracker/                  stop: done. A phone habit for drinking water.
      input.md                      the ramble, the only thing the skill is given
      key.md                        decided, open, and parked terms
      runs/run-1/decisions.md       turn 1, following the skill
      runs/score.md                 why it stopped, and the scorer output
    tidy-downloads/                 stop: open-cap. A command line tool for a downloads folder.
    lunch-poll/                     stop: done. A team bot that picks a lunch spot.
                                    each of the last two: input.md, key.md, runs/run-1/decisions.md, runs/score.md
```

Nothing here needs pstack. If it is installed, `/in-your-own-words` and `/sharpen` are optional helpers. The skill runs the same without them.

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
```

Every `run-1` passes the shape check and the score.
