# Attack review: keyword scorer

Synthetic stand-in for a claude pass. Same line, a head/ prefix, different words.

Verdict: needs fixes

## Tried
- Input: bug line bug line
  Observed: True
  Broke: YES stuffed words are enough
- Input: all good
  Observed: False
  Broke: No

## Findings
### F1 | head/score_review.py:6
Keyword stuffing with bug and line is scored as a pass.
Repro: the words bug, line, bug, line
Observed: True

## Held
all good did not pass. Input all good observed False.
