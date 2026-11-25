Synthetic stand-in for a codex pass. A failed case is accepted.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "{'passed': True, 'ok': False}", "broke": true, "observed": "True"},
    {"input": "{}", "broke": false, "observed": "False"}
  ],
  "findings": [
    {
      "file": "./report.py",
      "line": 4,
      "claim": "accept returns True when passed is true and a case has ok false.",
      "repro": "{'passed': True, 'ok': False}"
    }
  ]
}
```
