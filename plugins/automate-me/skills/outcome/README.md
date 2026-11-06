# outcome

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The brief's slots and traps come from `../brief-check/SKILL.md`.

Turns a rough idea, often a spoken ramble, into a brief an agent can run. It sorts what was said, fills the slots, marks every gap as an unknown with its question, and reads the brief back with at most 3 questions. Nothing runs until the user says yes.

Status: new. Four synthetic scored cases. The briefs in them were written by hand to show the scorer working, not produced by a skill run, so they say nothing yet about the skill's recall.

## What the checks cover, and what they don't

`check/check_brief.py` checks a brief's shape:

- every required slot is present once and filled (Goal, Decision, Context, Must-haves, Taste, Output, Verify, If stuck, Skills, Parking lot, Unknowns; Kind and Plan first are optional);
- every item that starts with `unknown` reads `unknown: <question>?`;
- the Unknowns list holds only unknown markers, and does not say `none` while a slot is unknown;
- a brief with unknowns has a Questions block, with at most 3 numbered questions, each with a question mark;
- no item is only trap adjectives (modern, clean, good, better, correct, valid, nice).

`check/score_case.py` scores a brief against a case key: facts in the speaker's words, slot terms, gaps asked rather than guessed, guesses that must not appear, and Parking lot items.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the sort into five piles (the key checks only its result in the brief);
- that the read-back comes before anything runs, and that nothing runs without a yes;
- that the 3 questions are the right ones, the gaps only the user can fill;
- the brief-check scoring and run at hand-off;
- the iterate step (only changed lines shown) and the learn step (offered once).

## Brief format

```
# Brief: <title>

- Kind: build | review | design | learn | search/decide
- Plan first: <optional>
- Goal: <value>
- Decision: <value, or unknown: <question>?>
- Must-haves:
  - <item>
  - <item>
...
- Unknowns:
  - unknown: <question>?

## Questions

1. <question>?
```

A slot is a top-level line `- <Label>: <value>`. Indented `  - ` lines under it are more items of that slot. An indented line that is not a bullet continues the item above it. The Questions block runs from a `## Questions` heading to the next heading.

The skill writes unknowns as `unknown: <question>?` with a colon, not a long dash, because the shared writing check bans long dashes (W1).

## Key format

A key is markdown. Only lines that start with one of these words are scored. Lines inside code blocks are skipped. Parts are separated by ` | `. A term written `a/b` matches either side. Matching ignores case.

| Line | Passes when |
|---|---|
| `Fact: <term>` | the term appears in the brief as written. A term that starts or ends with a letter or digit must not run into another one. So `10` does not match `100`, and `2600` does not match `2,600`. |
| `Slot: <Label> \| <term> \| ...` | that slot's items, joined, hold every term. |
| `Unknown: <id> \| <term> \| ...` | one unknown marker or one numbered question holds every term. The gap was asked, not guessed. |
| `Forbidden: <id> \| <regex>` | the regex (Python, case-insensitive) matches nowhere in the brief once every sentence that ends in `?` is removed. A match means the brief invented a fact. |
| `Parking: <id> \| <term> \| ...` | the Parking lot slot holds every term. |

Write one `Fact:` line per fact, so a miss names the fact. Keep a forbidden regex narrow enough that a correct brief cannot trip it, and give it a case where the regex fires in `runs/run-2` or in `check/test_score_case.py`.

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
      runs/run-1/brief.md           hand-written, passes (26 of 26)
      runs/run-2/brief.md           fails on purpose: guesses the cap, a move-in date and an area (19 of 26)
      runs/score.md                 why run-2 fails, and both scorer outputs
    erd-ramble/                     build: an ERD with two points still open
    prd-review-ramble/              review: a PRD path said with "I think", seed questions, a tangent
    learn-ramble/                   learn: indexes for a slow query; output is an explanation and a check
```

## Run the checks

From `outcome/`:

```
python3 check/test_check_brief.py
python3 check/test_score_case.py
for c in cases/*/; do
  for b in "$c"runs/*/brief.md; do
    python3 check/check_brief.py "$b" | tail -1
    python3 check/score_case.py "$c"key.md "$b" | tail -1
  done
done
```

Every `run-1` passes both. `apartment-search/runs/run-2` passes the shape check and fails the score, which is the point of it.
