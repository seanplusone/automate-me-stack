# Attack review: cap check

Synthetic stand-in for a claude pass. Same invented module, different path and words.

Verdict: needs fixes

## Tried
- Input: within_cap(5)
  Observed: False
  Broke: yes, off by one
- Input: within_cap(4)
  Observed: True
  Broke: no

## Findings
### F1 | cap.py:3
The comparison is less-than, so 5 falls outside a cap of 5.
Repro: call within_cap on 5
Observed: False

## Held
4 stayed inside the cap. Input within_cap(4) observed True.
