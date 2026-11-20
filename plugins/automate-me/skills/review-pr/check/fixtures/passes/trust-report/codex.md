# Attack review: trust report

Synthetic stand-in for a codex pass.

Verdict: needs fixes

## Tried
- Input: {'passed': True, 'cases': [{'name': 'a', 'ok': False}]}
  Observed: True
  Broke: yes
- Input: {}
  Observed: False
  Broke: no

## Findings
### F1 | ./report.py:4 | passes: codex
accept returns True when passed is true and a case has ok false.
Repro: {'passed': True, 'cases': [{'name': 'a', 'ok': False}]}
Observed: True

## Held
- Input: {}
  Observed: False
