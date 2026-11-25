# outcome

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The trap list comes from `../brief-check/SKILL.md`. The slot names below are this skill's.

Turns a rough idea, often a spoken ramble, into a brief an agent can run. It sorts what was said, fills the slots, marks every gap as an unknown with its question, and reads the brief back with at most 3 questions. Nothing runs until the user says yes. A shape-idea decisions.md is mapped into the brief instead of being sorted as a ramble.

Status: new. Five synthetic scored cases, plus `missing-evals`, which fails the shape check. The `run-*` briefs were written by hand to show the scorer working. One blind run has been scored. A fresh agent read only `SKILL.md` and brief-check's, never a key. Its scores and the key changes it led to are in each case's `runs/score.md`. Blind briefs are kept in `runs/blind/`.

## What the checks cover, and what they don't

`check/check_brief.py` checks a brief's shape:

- every required slot is present once and filled (Goal, Done, Output, Constraints, Tools, Agents and roles, Evals, Verification). Kind, Plan first, Taste, Skills, Parking lot and Unknowns are optional. A note in brackets after a label, as in `- Taste (flag, don't filter):`, is allowed;
- a top-level bullet (`-`, `*` or `+`) with a colon in its first 60 characters that is not one of those slots fails, as `unknown slot: <Label>`. A time such as 10:30 and a URL with `//` are not read as a label, so indent a bullet like `- mailto:x`. A label longer than 60 characters is not read as a label. A known slot written with another bullet or a space before the colon fails as an unknown slot. A sub-goal is its own brief, not a slot. Indented lines, fenced code and the Questions block are not read as slots.
- any item in any slot, and any Evals case, that is a placeholder fails. A slot whose items all fail is named. The value is normalized first. NFKC applies, and emphasis, code marks, one leading tag label and surrounding punctuation are stripped. Dots drop from `T.B.D.`, and `-`, `_` or `.` between letters reads as a space. A placeholder is then empty, or holds only words from a fixed list, with or without hedge words other than `not`. The words are tbd, tbc, tba, todo, fixme, xxx, n/a, na, none, pending, placeholder and later. The phrases are to be determined, to be decided, to be confirmed, fill in, fill in later, see below, see above and same as above. Words are Unicode, so non-English values are real. So are `make`, `$500`, `#123` and `24`. `none` alone is allowed on Skills, Parking lot and Unknowns, and beside other items. Tools and Constraints may use `none: <why>` when the reason is real. `write first: none` alone does not name a tool;
- a template hole fails only when it is unambiguous. The value is nothing but holes (`<goal>`, `< goal >`, `{{x}}`, `{x}`, `${x}`). Or it holds `[insert x]`, or is a line of the SKILL.md template. A hole inside a longer value, as in `Vec<String>` or `JSON {id, name}`, asks instead. Code spans and autolinks such as `<https://…>` and `<tel:…>` are never holes. `a < b` with a space is a comparison;
- Kind, when present, is one of build, review, design, learn, search/decide;
- Evals is present and its cases are not placeholders. A label is the word pass or fail followed by a colon, or should or must pass or fail, anywhere in an item outside code spans. A colon label's case runs to the next label. A phrase with nothing before it, as at the start of an item, is not a case. In an item that starts with a colon label, a phrase counts only when it ends the item. Text before the first colon label is judged too. When Evals has content but no pass case or no fail case can be found, the checker asks rather than fails. An `unknown: <question>?` Evals item stands in for the cases when the Questions block has a question;
- Plan first, when present, starts with `yes` or `none needed`;
- an `investigate:` item sits in Done, an `out of scope:` item in Constraints, and a `how:` item in Agents and roles;
- a slot that holds `unknown:` offers no default beside it;
- every unknown marker reads `unknown: <question>?`. A marker is `unknown` alone or an item that starts with `unknown:`, so `Unknown column names` is plain text;
- when Unknowns is present, it holds only unknown markers, and does not say `none` while a slot is unknown;
- a brief with unknowns has a Questions block, with at most 3 numbered questions, each with a question mark;
- no item is only trap adjectives (modern, clean, good, better, correct, valid, nice). A digit counts as a visible signal.

It exits 0 (PASS), 1 (FAIL), 2 (ASK) or 3 (usage). A usage error is bad arguments, or a file that is missing or not UTF-8 text. Any FAIL wins. Otherwise it asks about each value in a required slot, or Evals case, that it is in doubt about. It prints `ASK: <slot>: Is '<value>' a real answer for <slot>?` and exits 2. A value in doubt is only symbols that are not stripped punctuation (`→`, an emoji), or one word of one or two letters. So is a value of only hedge words. The hedge words are maybe, perhaps, possibly, probably, not, sure, unsure, unclear, depends, depending, it, idk, dunno, we, ll, will, well, see, yet, tbh, hmm, let and s. A hole inside a longer value, in any slot, asks `Is '<value>' a real answer for <slot>, or a hole to fill?`. Evals with content but no pass or fail case asks `Is there a pass case and a fail case here?`. The skill stops the hand-off there and asks the person. A yes goes in a block headed exactly `## Confirmed` at the end of the brief. It holds one `- <Slot>: <value>` line for each item or Evals case, and that value then passes. A no replaces the value.

The rule is deliberately narrow. check_brief FAILs only what is unambiguous. When in doubt it ASKs (exit 2, one ASK line each), and the agent stops and asks the person. Asking is cheap, and a wrong FAIL blocks a real brief. The read-back catches the rest. A placeholder outside the list, such as `Por determinar.`, passes.

### Limits

The check is a review aid, not a gate on meaning. It reads wording, so it misses some cases:
- Evals labels in other words, such as `Should pass:` or `Must pass:`, can fail.
- Outline-style Evals, with the case on a nested line under `Pass:`, can fail.
- A short verification command that holds a vague word, such as `make clean`, can be flagged as vague.
- A checklist item such as `[x] TBD` can pass.
- An Evals case that only repeats its label, such as `Pass: pass`, can pass.
- A placeholder with text after it, such as `TBD by Friday`, can pass.

The read-back and the ASK outcome are the backstop.
There are too few real examples to judge wording reliably, so when the check is unsure it asks the person (ASK) rather than deciding.
Save each confirmed answer as a new test case.
As cases build up, more calls can move from asking to automatic, but only after they hold on fresh briefs.

Other skills import `classify(value)` (`"pass"`, `"fail"` or `"ask"`), `judge(value)` (the outcome and why), `is_placeholder`, `eval_cases`, `case_is_real`, `check`, `asks` and `ask_lines` from `check/check_brief.py`. `breakdown/check_plan.py` judges every plan field that lands in a prompt, then runs `check` on each rendered prompt.

`check/score_case.py` scores a brief against a case key: facts in the speaker's words, slot terms, gaps asked rather than guessed, guesses that must not appear, and Parking lot items.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the sort into five piles, including self-corrections and hedges (the key checks only its result in the brief);
- the "Check even if unsaid" limits for each kind (a key checks them only where the case names them);
- that the read-back comes before anything runs, and that nothing runs without a yes;
- that the 3 questions are the right ones, ranked decision, then limits and scope, then intent;
- the checker and the trap list at hand-off;
- the iterate step (only changed lines shown) and the learn step (offered once).

## Blind runs

The `run-1` and `run-2` briefs are hand-written: they prove the scorers work, not the skill. The real eval is a blind run. A fresh agent gets only `SKILL.md`, `../brief-check/SKILL.md` and each case's `input.md`. It never sees a key or another run, and it writes the read-back brief for each case. Those briefs are scored with `check/score_case.py`.

| Run | Skill version | apartment-search | erd-ramble | prd-review-ramble | learn-ramble | Total | Invented facts |
|---|---|---|---|---|---|---|---|
| Blind 1 | first draft | 20/26 | 17/19 | 17/18 | 16/18 | 70/81 | 0 |
| Blind 2 | after the fixes below | 24/28 | 17/19 | 18/18 | 17/18 | 76/83 | 0 |

Blind 1 is scored with the whole-word scorer. Its first, substring scorer counted "pet" inside "carpet" as asking about pets. Between the runs, some keys were loosened where the blind brief was right and the key too literal, and kept strict where the skill really missed. Each change and its reason is in that case's `runs/score.md`. Blind 2's briefs are kept in each case's `runs/blind/`.

Known gaps after blind 2, left as they are because a fix would need another blind run:

- In a search, it can still miss limits the speaker never mentioned, like area or pets.
- It sometimes picks a visible signal for an adjective ("looks clean") instead of asking for one.
- It puts a few items in a fair slot that the key does not expect, such as the floor rule under Done and not Taste.

## Brief format

Required: Goal, Done, Output, Constraints, Tools, Agents and roles, Evals, Verification.
Optional, omitted when empty: Kind, Plan first, Taste, Skills, Parking lot, Unknowns.

Where the old names went:

| Old slot | Now |
|---|---|
| Goal, and Decision (it was split out of Goal) | Goal |
| Must-haves, including `investigate:` | Done |
| Output | Output, including how the person wants to see it |
| If stuck, and `out of scope:` | Constraints |
| Context, when it named a file, a system or a tool | Tools, with `write first:` |
| the `how:` line that was under Skills | Agents and roles |
| Verify | Verification |
| Kind, Plan first, Taste, Skills, Parking lot, Unknowns | still those slots, now optional |

Evals is new. It is one pass case and one fail case. It is not Done and it is not Verification.

```
# Brief: <title>

- Goal: <what to do>
- Done:
  - <observable criterion>
  - investigate: <question the agent answers by looking>
- Output: <what comes back, and how the person sees it>
- Constraints:
  - <guardrail>
  - out of scope: <exclusion>
- Tools:
  - <tool>
  - write first: <what must be written first, or none>
- Agents and roles:
  - how: <how the work is split>
- Evals:
  - Pass: <one case>
  - Fail: <one case>
- Verification: <how each claim is proved>

## Questions

1. <question>?
```

A slot is a top-level line `- <Label>: <value>`. Indented `  - ` lines under it are more items of that slot. An indented line that is not a bullet continues the item above it. The Questions block runs from a `## Questions` heading to the next heading.

The skill writes unknowns as `unknown: <question>?` with a colon, not a long dash, because the shared writing check bans long dashes (W1).

## Key format

A key is markdown. Only lines that start with one of these words are scored. Lines inside code blocks are skipped. Parts are separated by ` | `. A term written `a/b` matches either side. Matching ignores case.

A term (in Slot, Any, Unknown and Parking lines) matches at the start of a word. So `pet` matches "pets" but not "carpet". A term of 3 letters or fewer must be the whole word, or that word plus s, so `ERD` does not match "erDiagram". A term that ends in a digit must end the number, and a term of several words matches as a phrase. Pick terms that cannot mean something else in a brief. The bare word `version` matched "the standup version" until it became `postgres version`.

| Line | Passes when |
|---|---|
| `Fact: <term>` | the term appears in the brief as written. A term that starts or ends with a letter or digit must not run into another one. So `10` does not match `100`, and `2600` does not match `2,600`. |
| `Slot: <Label> \| <term> \| ...` | that slot's items, joined, hold every term. |
| `Any: <id> \| <term> \| ...` | the brief holds every term, in any slot. Use it when the slot is a fair judgment call, such as where a tool is named. |
| `Unknown: <id> \| <term> \| ...` | one unknown marker or one numbered question holds every term. The gap was asked, not guessed. |
| `Forbidden: <id> \| <regex>` | the regex (Python, case-insensitive) matches nowhere in the brief once every sentence that ends in `?` is removed. A match means the brief invented a fact. |
| `Parking: <id> \| <term> \| ...` | the Parking lot slot holds every term. |

Write one `Fact:` line per fact, so a miss names the fact. When a blind run misses a key item, decide whether the key was too literal or the skill missed. Loosen only the first kind. Record each change and its reason in `runs/score.md` under "Key changes after blind run". Keep a forbidden regex narrow enough that a correct brief cannot trip it, and give it a case where the regex fires in `runs/run-2` or in `check/test_score_case.py`.

## Layout

```
outcome/
  README.md                         this file
  SKILL.md                          sort, fill, mark unknowns, read back, hand off
  check/
    check_brief.py                  the shape check
    score_case.py                   scores a brief against a case key
    test_check_brief.py             python3 check/test_check_brief.py
    test_score_case.py              python3 check/test_score_case.py
  cases/
    apartment-search/               search/decide: a rent split, a stretch budget, photos over descriptions
      input.md                      the ramble, the only thing the skill is given
      key.md                        facts, slot terms, unknowns, forbidden guesses, parking lot
      runs/run-1/brief.md           hand-written, passes (28 of 28)
      runs/run-2/brief.md           fails on purpose: guesses the cap, a move-in date and an area (21 of 28)
      runs/score.md                 why run-2 fails, the blind score, key changes, scorer outputs
    erd-ramble/                     build: an ERD with two points still open
    prd-review-ramble/              review: a PRD path said with "I think", questions to look up, a tangent
    learn-ramble/                   learn: indexes for a slow query; output is an explanation and a check
    badge-ramble/                   build: a badge on a bell icon; output says where it lives and what shares that space
                                    each of the last four: input.md, key.md, runs/run-1/brief.md, runs/score.md
    missing-evals/                  shape only: a brief with every required slot except Evals
      runs/run-1/brief.md           check_brief.py fails, and the only failure is "missing slot: Evals"
```

## Run the checks

From `outcome/`:

```
set -euo pipefail
python3 check/test_check_brief.py
python3 check/test_score_case.py
for c in cases/*/; do
  base=$(basename "$c")
  if [ "$base" = missing-evals ]; then
    continue
  fi
  if [ "$base" = from-decisions ]; then
    for d in "$c"*/decisions.md; do
      tmp=$(mktemp)
      python3 check/map_decisions.py "$d" > "$tmp"
      python3 check/check_brief.py "$tmp"
      rm -f "$tmp"
    done
    continue
  fi
  for b in "$c"runs/*/brief.md; do
    python3 check/check_brief.py "$b"
  done
  python3 check/score_case.py "$c"key.md "$c"runs/run-1/brief.md
done
```

Every `run-1` passes both checks. The loop checks the shape of every other brief under `runs/`, and it scores `run-1` only. `from-decisions` has a `decisions.md` and no `runs/` or key. The loop maps each file and runs `check_brief.py` on the result. `map_decisions.py` runs shape-idea's `check_decisions.py` first, with the same `confirmed.md`. It prints a brief only on exit 0. Exit 1 prints the format errors, and exit 2 prints the CHECK WITH ME list. Each yes the user gives goes in `confirmed.md` next to the decisions file, and the mapper copies it into the brief's `## Confirmed` block. `set -e` stops the loop when any command fails. `apartment-search/runs/run-2` passes the shape check and fails the score, which is the point of it, so score it on its own:

```
python3 check/score_case.py cases/apartment-search/key.md cases/apartment-search/runs/run-2/brief.md
```

`missing-evals` has no key. Its brief fails `check_brief.py` on the missing Evals slot, and that is the point of it. Skip it in the loop above. Check it on its own:

```
python3 check/check_brief.py cases/missing-evals/runs/run-1/brief.md
```
