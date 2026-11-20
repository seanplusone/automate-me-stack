# Attack review: item cap

Verdict: needs fixes

## Tried
- Input: within_cap(5)
  Observed: False
  Broke: yes

## Findings
### F1 | head/cap.py:3 | passes: codex
within_cap(5) returns False.

## Held
- Input: within_cap(4)
  Observed: True
