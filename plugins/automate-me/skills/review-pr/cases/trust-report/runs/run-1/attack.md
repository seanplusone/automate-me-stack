# Attack review: trust report

Verdict: needs fixes

## Tried
- Input: python3 test_report.py
  Observed: 2 passed
  Broke: no

- Input: {'passed': True, 'cases': [{'name': 'a', 'ok': False}]}
  Observed: True
  Broke: yes

- Input: {'passed': False, 'cases': [{'name': 'a', 'ok': False}]}
  Observed: False
  Broke: no

- Input: {'passed': True, 'cases': 'bad'}
  Observed: True
  Broke: yes

- Input: {'passed': True}
  Observed: True
  Broke: yes

- Input: {}
  Observed: False
  Broke: no

## Findings
### F1 | report.py:4 | passes: current
accept returns True when passed is True and a case has ok False.
Repro: {'passed': True, 'cases': [{'name': 'a', 'ok': False}]}
Observed: True

## Held
- Input: python3 test_report.py
  Observed: 2 passed

- Input: {'passed': False, 'cases': [{'name': 'a', 'ok': False}]}
  Observed: False

- Input: {}
  Observed: False
