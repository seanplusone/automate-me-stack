# Attack review: report check

Synthetic stand-in for a claude pass. The path includes the case directory.

Verdict: needs fixes

## Tried
- Input: {'passed': True, 'cases': [{'name': 'a', 'ok': False}]}
  Observed: True
  Broke: Yes
- Input: {}
  Observed: False
  Broke: no

## Findings
### F1 | cases/trust-report/head/report.py:4 | passes: claude
The summary field is trusted, so a failed case is accepted.
Repro: passed true with ok false
Observed: True

## Held
The empty report was rejected. Input {} observed False.
