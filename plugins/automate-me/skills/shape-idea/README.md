# shape-idea

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The next step is [outcome](../outcome/SKILL.md).

Brainstorms a vague idea before a brief. Each turn restates the idea, asks one question, and names at most one risk. Decisions are saved to `decisions.md` as they are made. It stops when the five slots are decided, at turn 10, or after turn 1 when more than 5 other gaps stay open. Then it hands the file to outcome. It never builds, runs, or posts.

Status: new. Four synthetic scored cases. Each `run-1` was written by a fresh model that read only `SKILL.md` and that case's `input.md`. The input holds the whole conversation. Keys were written from the input, not from the run. habit-tracker, tidy-downloads, and lunch-poll stop at `done`. bookmark-box stops at `open-cap`.

## What the checks cover, and what they don't

`check/check_decisions.py` checks a finished file's shape:

- `## Decided`, `## Open`, `## Parked`, and `## Handoff` are present once, in that order;
- every Open item ends with `?`, or `?` and a closing quote or bracket (a lone `none` means the section is empty). Only the end counts, so `Should the button say 'What's next?' or 'Continue'?` is one question. The question after any `tools:`, slot or `unknown:` label is not only a placeholder such as `?` or `TBD?`, and holds no template hole such as `<channel>`;
- the file maps to a brief that passes outcome's `check_brief.py`. The check maps the file with outcome's mapper and runs the brief check's `check()` and `asks()` on that brief. A placeholder, a template hole, a trap word such as "clean", a tag outside its slot, or a default beside an unknown fails as it does in the brief. Each line the mapper prefixes with `stated:` is judged again without it;
- a Decided value does not end in `?`. Move a question to Open;
- `stop` is `done`, `turn-cap`, or `open-cap`, once;
- each of goal, done, output, verify, and constraints starts one Decided line or one Open line, with a value, and not both;
- a hole inside a longer value, such as `the form submits on <Enter>`, asks in any Decided, Open or Parked line, as the brief check does. An Open item that is only a hole fails. A hole inside inline code and an autolink such as `<https://example.org>` are fine;
- no answer is an unknown. An answer is a Decided value, an Evals case, or a Parked `out of scope:` line. Its first word, once markup, quotes, brackets, link syntax and every leading label (`stated:`, `out of scope:`, `how:` and the rest) are gone, is not `unknown` followed by nothing, by punctuation, or by at most two words. `unknown for now`, `(unknown), CSV or JSON` and `[unknown](https://example.org)` fail. Move it to Open as a question. A longer value, such as `unknown senders get nothing`, asks whether it is decided;
- no label is left with nothing after it. `decide: stated:`, `tools: stated:`, a lone `stated:` and `out of scope: stated:` fail with a message that names the line;
- text inside a ``` or ~~~ fence, of any length, including a nested fence, is not a decision. A fence under Decided, Open or Parked fails, because its text would be lost. An unclosed fence fails;
- a Decided `tools:`, `agents:` (or `agents and roles:`), `evals:`, `decide:`, or `write first:` line has a value and is not repeated. Bold and a singular label (`**tools:**`, `tool:`, `eval:`) name the same line. An `evals:` line with no pass case or no fail case asks, as the brief check does. The five slots stay the only required ones;
- `stop: done` requires all five Decided and none of them Open;
- `stop: open-cap` is only after turn 1, and only with more than 5 Open lines that are not slots;
- `stop: turn-cap` requires `turns: 10`;
- `turns` is an ASCII whole number from 1 through 10;
- the shared writing check passes on the file, whether or not the line says `writing: pass`;
- no item runs past one line;
- Handoff has `next: /automate-me:outcome`, a single `writing: pass` line, and one `map:` line.

Exit 0 when every check passed. Exit 1 when any check failed. Exit 2 when nothing failed but a value needs the person. Exit 3 on a usage error: bad arguments, or a path that is missing, a directory, or not UTF-8 text. It prints one line on stderr.

Exit 2 is a break point. The check prints one `ASK: <slot>: Is '<value>' a real answer for <slot>?` line for each value that outcome's brief check asks about on the mapped brief, such as `output: ok`, `decide: maybe` or a Parked `out of scope: AI`. It prints `ASK: <slot>: Is '<value>' decided, or still unknown?` for a long answer that starts with "unknown", and `ASK: Unknowns: Is '<question>' a real question, or a hole to fill?` for an Open question with a hole inside it. A prefix such as `stated:` or `how:` does not hide the value. The skill stops, asks the person that yes/no question, and records the answer. A yes goes under an optional `## Confirmed` section after Handoff, as `- <Slot>: <value>`. The mapper copies that section into the brief, so the brief check does not ask again. A no replaces the value. A confirmation never lifts a failure.

The placeholder list is outcome's, and it is deliberately narrow. A phrase off the list, such as "see notes", passes. A phrase of only hedge words, such as "not sure yet", is an ASK. The ask and outcome's read-back catch the rest.

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

Outcome reads `goal:` as Goal, `done:` as Done, `output:` as Output, `constraints:` as Constraints, and `verify:` as Verification. Tools, Agents and roles, and Evals stay unknown until the user answers, unless a Decided `tools:`, `agents:` or `evals:` line already fills that slot. An Open `tools:`, `agents:`, `evals:` or `decide:` question takes the place of outcome's stock question for that slot. Open is Unknowns. Parked is the Parking lot. A slot that is still open is an unknown, not a filled slot. A Decided `out of scope:` line goes to Constraints. A Decided `decide:` line goes to Goal. Without one, the decide question goes to Unknowns and the Questions block, not Goal. A Confirmed section goes to the brief's Confirmed block.

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
set -euo pipefail
python3 check/test_check_decisions.py
python3 check/test_score_case.py
python3 check/test_judge.py
python3 check/test_break.py
for c in cases/*/; do
  python3 check/check_decisions.py "$c"runs/run-1/decisions.md
  python3 check/score_case.py "$c"key.md "$c"runs/run-1/decisions.md
done
python3 ../shared/check_writing.py SKILL.md
for c in cases/*/; do
  python3 ../shared/check_writing.py "$c"runs/run-1/decisions.md
done
```

`set -e` stops the loop at the first command that fails.

Every `run-1` passes the shape check and the keyword score. The meaning judge is separate:

```
python3 check/judge_case.py cases/<name>/key.md cases/<name>/runs/run-1/decisions.md
```

It runs `codex exec` or `claude -p` when one is on PATH, and prints SKIP and exits 0 when neither is.
