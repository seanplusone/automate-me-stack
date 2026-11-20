# Attack review: word score

Verdict: needs fixes

## Tried
- Input: python3 test_score_review.py
  Observed: 1 passed
  Broke: no
- Input: bug line bug line
  Observed: True
  Broke: yes
- Input: bug at line 3
  Observed: True
  Broke: no
- Input: all good
  Observed: False
  Broke: no
- Input: accept returns True at report.py:4 for input x
  Observed: False
  Broke: yes
- Input: ""
  Observed: False
  Broke: no

## Findings
### F1 | score_review.py:6 | passes: current
passes returns True for the text bug line bug line, which names no defect.
Repro: bug line bug line
Observed: True

### F2 | score_review.py:6 | passes: current
passes returns False for a review that names a file, a line and an input.
Repro: accept returns True at report.py:4 for input x
Observed: False

## Held
- Input: python3 test_score_review.py
  Observed: 1 passed
- Input: bug at line 3
  Observed: True
- Input: all good
  Observed: False
- Input: ""
  Observed: False
