# Attack review: item cap

Synthetic stand-in for a codex pass. The module is invented.

Verdict: needs fixes

## Tried
- Input: within_cap(5)
  Observed: False
  Broke: YES the boundary is rejected
- Input: within_cap(4)
  Observed: True
  Broke: No, 4 is allowed

## Findings
### F1 | head/cap.py:3 | passes: codex
within_cap(5) returns False, so a full list of 5 is rejected.
Repro: within_cap(5)
Observed: False

## Held
- Input: within_cap(4)
  Observed: True
