# Attack review: item cap

Verdict: needs fixes

## Tried
- Input: python3 case_test_cap.py
  Observed: 2 passed
  Broke: no
- Input: within_cap(4)
  Observed: True
  Broke: no
- Input: within_cap(5)
  Observed: False
  Broke: yes
- Input: within_cap(6)
  Observed: False
  Broke: no
- Input: within_cap(0)
  Observed: True
  Broke: no

## Findings
### F1 | cap.py:3 | passes: current
within_cap returns False for 5, so the cap of 5 rejects a full list.
Repro: within_cap(5)
Observed: False

## Held
- Input: python3 case_test_cap.py
  Observed: 2 passed
- Input: within_cap(4)
  Observed: True
- Input: within_cap(6)
  Observed: False
- Input: within_cap(0)
  Observed: True
