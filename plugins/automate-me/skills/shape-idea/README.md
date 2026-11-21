# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops when the five slots are decided, at turn 10, or after turn 1 when more than 5 other gaps stay open. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Four synthetic scored cases. Each `run-1` was written by a fresh model that read only `SKILL.md` and that case's `input.md`. The input holds the whole conversation. Keys were written from the input, not from the run. habit-tracker, tidy-downloads, and lunch-poll stop at `done`. bookmark-box stops at `open-cap`.

## What the checks cover, and what they don't

`check/check_decisions.py` checks a finished file's shape:

- `## Decided`, `## Open`, `## Parked`, and `## Handoff` are present once, in that order;
- every Open item ends with `?` (a lone `none` means the section is empty);
- Open has at most 5 items;
- `stop` is `done`, `turn-cap`, or `open-cap`, once;
- `turns` is one whole number from 0 through 10;
- each of goal, done, output, verify, and constraints starts one Decided line or one Open line, with a value, and not both;
- `stop: done` requires all five Decided and none of them Open;
- `stop: open-cap` is only after turn 1, and only with more than 5 Open lines that are not slots;
- `stop: turn-cap` requires `turns: 10`;
- `turns` is an ASCII whole number from 1 through 10;
- the shared writing check passes on the file, whether or not the line says `writing: pass`;
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
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
```

Outcome reads `goal:` as Goal, `done:` as Done, `output:` as Output, `constraints:` as Constraints, and `verify:` as Verification. Tools, Agents and roles, and Evals stay unknown until the user answers. Open is Unknowns. Parked is the Parking lot. A slot that is still open is an unknown, not a filled slot.

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
    habit-tracker/                  stop: done, turn 3. A phone habit for drinking water.
      input.md                      the ramble, the only thing the skill is given
      key.md                        decided, open, and parked terms
      runs/run-1/decisions.md       following the skill
      runs/score.md                 why it stopped, and the scorer output
    tidy-downloads/                 stop: done, turn 5. A command line tool for a downloads folder.
    lunch-poll/                     stop: done, turn 3. A team bot that picks a lunch spot.
    bookmark-box/                   stop: open-cap, turn 2. A phone box for saving links.
                                    each of the last two: input.md, key.md, runs/run-1/decisions.md, runs/score.md
```

Nothing here needs pstack. If it is installed, `/in-your-own-words` and `/sharpen` are optional helpers, and `/unslop` is an extra pass after the shared writing check. If it is not installed, skip that pass. The skill runs the same without them.

## Run the checks

From `shape-idea/`:

```
python3 check/test_check_decisions.py
python3 check/test_score_case.py
python3 check/test_judge.py
python3 check/test_break.py
for c in cases/*/; do
  python3 check/check_decisions.py "$c"runs/run-1/decisions.md | tail -1
  python3 check/score_case.py "$c"key.md "$c"runs/run-1/decisions.md | tail -1
done
python3 ../shared/check_writing.py SKILL.md
for c in cases/*/; do
  python3 ../shared/check_writing.py "$c"runs/run-1/decisions.md | tail -1
done
```

Every `run-1` passes the shape check and the keyword score. The meaning judge is separate:

```
python3 check/judge_case.py cases/<name>/key.md cases/<name>/runs/run-1/decisions.md
```

It runs `codex exec` or `claude -p` when one is on PATH, and prints SKIP and exits 0 when neither is.
