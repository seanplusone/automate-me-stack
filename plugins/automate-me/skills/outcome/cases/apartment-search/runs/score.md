# Score: apartment-search

A synthetic case. Runs 1 and 2 were written by hand to show how a case is scored; run 2 is built to fail. A blind run came later.
The blind brief was written by a fresh agent that read only this skill's SKILL.md and brief-check's SKILL.md, never the key or the runs. It lives outside the repo, in the session scratch folder, and is not copied here.

| | run-1 | run-2 | blind |
|---|---|---|---|
| Brief | hand-written, every gap asked | run-1 with four gaps filled by guesses | fresh agent, SKILL.md only |
| `check_brief.py` | PASS | PASS | FAIL (Plan first is an unknown; Output offers a default beside an unknown) |
| `score_case.py`, first key and scorer | PASS, 26 of 26 | FAIL, 19 of 26 | FAIL, 21 of 26 |
| `score_case.py`, fixed scorer, first key | PASS, 26 of 26 | FAIL, 19 of 26 | FAIL, 20 of 26 |
| `score_case.py`, fixed scorer, current key | PASS, 28 of 28 | FAIL, 21 of 28 | FAIL, 25 of 28 |
| `check_writing.py` | PASS | PASS | not run here |

Run 2 passes `check_brief.py`. The shape check and the case score measure different things. A brief can have every slot filled and still fill one with a guess.

## Why run-2 fails

- **Decision filled.** Run 2 writes "Pick the top 3 to tour this weekend." The speaker never said what the shortlist is for, so the key wants it asked (`unknown decision`).
- **Cap guessed.** Run 2 turns the rent split into "Budget cap of 4300 a month." The speaker gave 2600 and 1700 as a split and 5k as a stretch. Which number is the cap was never said. The key fails both the missing question (`unknown cap`) and the guess (`forbidden 4300 as the cap`).
- **Move-in date invented.** "Move-in by March 1" appears nowhere in the input. It fails `unknown move-in` and `forbidden move-in date`.
- **Neighborhoods invented.** "Woodbridge or Turtle Rock" are guesses at an area the speaker never named. It fails `unknown area` and `forbidden neighborhood`.
- Pets are still asked, so `unknown pets` is found. Every fact, slot term and the parking lot item still match.

## Scorer fix after the blind run

The first scorer matched terms as substrings. The key term `pet` matched "carpet" in the blind brief, so `unknown pets` scored found when the brief never asks about pets. Terms now match at the start of a word, and a term that ends in a digit must end the number. A term of 3 letters or fewer must be the whole word or its plural. A sweep of every key term against every brief found one more collision of that kind, `ERD` inside "erDiagram". The blind score dropped from 21 to 20 on the same key. `check/test_score_case.py` has the carpet case.

## Key changes after blind run

- `Slot: If stuck | next 100/$100` became `Any: peek | next 100`. Too literal. The blind brief kept the peek in the speaker's words but put it in Unknowns, because "under the max" names no max. That is a fair reading, and the `Fact:` line already requires "100 dollars".
- Added `Slot: If stuck | never loosen`. If stuck is still scored, now on brief-check's own stop rule instead of on where the peek sits.
- `Slot: Skills | browser | save what worked` became `Slot: Skills | save what worked` plus `Any: tool | browser`. Too literal. The trap asks that the tool be named; the blind brief named the browser in If stuck.
- `Slot: Plan first | parallel` became `Any: parallel | parallel`. SKILL.md now puts process asks in Skills as `how:` and makes Plan first `yes` or `none needed`, so the slot it named moved.
- `Unknown: cap | 4300 | 5k/5000` became `Unknown: cap | cap/ceiling/limit | 5k/5000`. Too literal. The blind brief asked for the cap without printing the sum, which is what SKILL.md asks for ("do not add them up").
- Kept strict: `unknown move-in`, `unknown area` and `unknown pets`. The blind brief never asks about timing, area or pets. Timing and location are now in SKILL.md's "Check even if unsaid" table for search/decide. Pets remain a case-specific gap with no generic rule, so this miss is expected to stay until a run asks it unprompted.

Blind misses on the current key are move-in, area and pets, all real skill misses.

Output of `python3 check/score_case.py cases/apartment-search/key.md cases/apartment-search/runs/run-1/brief.md` (exit 0):

```
facts 3 bed: found
facts 2 bath: found
facts Irvine: found
facts 2600: found
facts 1700: found
facts 5k/5000: found
facts 10: found
facts 100 dollars/$100: found
slot Kind: found
slot Taste: found
slot Verify: found
slot Output: found
any parallel: found
slot Must-haves: found
slot If stuck: found
slot Skills: found
any peek: found
any tool: found
unknown decision: found
unknown move-in: found
unknown cap: found
unknown area: found
unknown pets: found
forbidden move-in date: clear
forbidden neighborhood: clear
forbidden pet policy: clear
forbidden 4300 as the cap: clear
parking facebook: found
PASS 28/28 key items
```

Output of `python3 check/score_case.py cases/apartment-search/key.md cases/apartment-search/runs/run-2/brief.md` (exit 1):

```
facts 3 bed: found
facts 2 bath: found
facts Irvine: found
facts 2600: found
facts 1700: found
facts 5k/5000: found
facts 10: found
facts 100 dollars/$100: found
slot Kind: found
slot Taste: found
slot Verify: found
slot Output: found
any parallel: found
slot Must-haves: found
slot If stuck: found
slot Skills: found
any peek: found
any tool: found
unknown decision: MISSED no unknown or question names: tour/apply
unknown move-in: MISSED no unknown or question names: move-in/move in
unknown cap: MISSED no unknown or question names: cap/ceiling/limit, 5k/5000
unknown area: MISSED no unknown or question names: commute/neighborhood/area
unknown pets: found
forbidden move-in date: MISSED guessed a fact: 'Move-in by March'
forbidden neighborhood: MISSED guessed a fact: 'Woodbridge'
forbidden pet policy: clear
forbidden 4300 as the cap: MISSED guessed a fact: 'Budget cap of 4300'
parking facebook: found
FAIL 21/28 key items
```

Output of `python3 check/score_case.py cases/apartment-search/key.md <blind>/apartment-search/brief.md` (exit 1):

```
facts 3 bed: found
facts 2 bath: found
facts Irvine: found
facts 2600: found
facts 1700: found
facts 5k/5000: found
facts 10: found
facts 100 dollars/$100: found
slot Kind: found
slot Taste: found
slot Verify: found
slot Output: found
any parallel: found
slot Must-haves: found
slot If stuck: found
slot Skills: found
any peek: found
any tool: found
unknown decision: found
unknown move-in: MISSED no unknown or question names: move-in/move in
unknown cap: found
unknown area: MISSED no unknown or question names: commute/neighborhood/area
unknown pets: MISSED no unknown or question names: pet
forbidden move-in date: clear
forbidden neighborhood: clear
forbidden pet policy: clear
forbidden 4300 as the cap: clear
parking facebook: found
FAIL 25/28 key items
```
