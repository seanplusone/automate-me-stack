# outcome

Part of `automate-me`. Shared writing rules live in `../shared/writing-rules.md`. The brief's slots and traps come from `../brief-check/SKILL.md`.

Turns a rough idea, often a spoken ramble, into a brief an agent can run. It sorts what was said, fills the slots, marks every gap as an unknown with its question, and reads the brief back with at most 3 questions. Nothing runs until the user says yes.

Status: new. Four synthetic scored cases. The `run-*` briefs were written by hand to show the scorer working. One blind run has been scored. A fresh agent read only `SKILL.md` and brief-check's, never a key. Its scores and the key changes it led to are in each case's `runs/score.md`. Its briefs live outside the repo.

## What the checks cover, and what they don't

`check/check_brief.py` checks a brief's shape:

- every required slot is present once and filled (Plan first, Goal, Decision, Context, Must-haves, Taste, Output, Verify, If stuck, Skills, Parking lot, Unknowns; Kind is optional). A note in brackets after a label, as in `- Taste (flag, don't filter):`, is allowed;
- Plan first starts with `yes` or `none needed`;
- an `investigate:` or `out of scope:` item sits in Must-haves, and a `how:` item in Skills;
- a slot that holds `unknown:` offers no default beside it;
- every item that starts with `unknown` reads `unknown: <question>?`;
- the Unknowns list holds only unknown markers, and does not say `none` while a slot is unknown;
- a brief with unknowns has a Questions block, with at most 3 numbered questions, each with a question mark;
- no item is only trap adjectives (modern, clean, good, better, correct, valid, nice).

`check/score_case.py` scores a brief against a case key: facts in the speaker's words, slot terms, gaps asked rather than guessed, guesses that must not appear, and Parking lot items.

Neither script checks the flow in `SKILL.md`. These parts are instructions only, checked by a person reading the transcript:

- the sort into five piles, including self-corrections and hedges (the key checks only its result in the brief);
- the "Check even if unsaid" limits for each kind (a key checks them only where the case names them);
- that the read-back comes before anything runs, and that nothing runs without a yes;
- that the 3 questions are the right ones, ranked decision, then limits and scope, then intent;
- the brief-check scoring and run at hand-off;
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
- It puts a few items in a fair slot that the key does not expect, such as the floor rule under Must-haves and not Taste.

## Brief format

```
# Brief: <title>

- Kind: build | review | design | learn | search/decide
- Plan first: yes: <plan> | none needed
- Goal: <value>
- Decision: <value, or unknown: <question>?>
- Must-haves:
  - <item>
  - investigate: <question the agent answers by looking>
  - out of scope: <exclusion>
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
                                    each of the last three: input.md, key.md, runs/run-1/brief.md, runs/score.md
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
