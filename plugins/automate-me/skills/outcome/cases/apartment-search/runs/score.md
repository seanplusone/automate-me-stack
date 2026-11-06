# Score: apartment-search

A synthetic case: both briefs were written by hand to show how a case is scored. They were not produced by a skill run, so this shows the scorer working, not the skill's recall. Run 2 is built to fail.

| | run-1 | run-2 |
|---|---|---|
| Brief | hand-written, every gap asked | run-1 with four gaps filled by guesses |
| `check_brief.py` | PASS | PASS |
| `score_case.py` | PASS, 26 of 26 | FAIL, 19 of 26 |
| `check_writing.py` | PASS | PASS |

Both runs pass `check_brief.py`. The shape check and the case score measure different things. A brief can have every slot filled and still fill one with a guess.

## Why run-2 fails

- **Decision filled.** Run 2 writes "Pick the top 3 to tour this weekend." The speaker never said what the shortlist is for, so the key wants it asked (`unknown decision`).
- **Cap guessed.** Run 2 turns the rent split into "Budget cap of 4300 a month." The speaker gave 2600 and 1700 as a split and 5k as a stretch. Which number is the cap was never said. The key fails both the missing question (`unknown cap`) and the guess (`forbidden 4300 as the cap`).
- **Move-in date invented.** "Move-in by March 1" appears nowhere in the input. It fails `unknown move-in` and `forbidden move-in date`.
- **Neighborhoods invented.** "Woodbridge or Turtle Rock" are real-sounding guesses at an area the speaker never named. It fails `unknown area` and `forbidden neighborhood`.
- Pets are still asked, so `unknown pets` is found. Every fact, slot term and the parking lot item still match.

Run 1 asks the decision and the cap as their own questions, and folds move-in, area and pets into the third. Its Unknowns list keeps all five.

Output of `python3 check/score_case.py cases/apartment-search/key.md cases/apartment-search/runs/run-1/brief.md` (exit 0), run from `outcome/`:

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
slot Plan first: found
slot Must-haves: found
slot If stuck: found
slot Skills: found
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
PASS 26/26 key items
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
slot Plan first: found
slot Must-haves: found
slot If stuck: found
slot Skills: found
unknown decision: MISSED no unknown or question names: tour/apply
unknown move-in: MISSED no unknown or question names: move-in/move in
unknown cap: MISSED no unknown or question names: 4300, 5k/5000
unknown area: MISSED no unknown or question names: commute/neighborhood/area
unknown pets: found
forbidden move-in date: MISSED guessed a fact: 'Move-in by March'
forbidden neighborhood: MISSED guessed a fact: 'Woodbridge'
forbidden pet policy: clear
forbidden 4300 as the cap: MISSED guessed a fact: 'Budget cap of 4300'
parking facebook: found
FAIL 19/26 key items
```
