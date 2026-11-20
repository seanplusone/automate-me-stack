# Attack review: word score

Synthetic stand-in for a codex pass.

Verdict: needs fixes

## Tried
- Input: bug line bug line
  Observed: True
  Broke: yes
- Input: all good
  Observed: False
  Broke: no

## Findings
### F1 | score_review.py:6 | passes: codex
passes returns True for the text bug line bug line, which names no defect.
Repro: bug line bug line
Observed: True

## Held
- Input: all good
  Observed: False
