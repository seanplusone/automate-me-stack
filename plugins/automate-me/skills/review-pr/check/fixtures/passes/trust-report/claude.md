Synthetic stand-in for a claude pass. The path includes the case directory.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "{'passed': True, 'ok': False}", "broke": true, "observed": "True"},
    {"input": "{}", "broke": false, "observed": "False"}
  ],
  "findings": [
    {
      "file": "cases/trust-report/head/report.py",
      "line": 3,
      "claim": "The summary field is trusted, so a failed case is accepted.",
      "repro": "passed true with ok false"
    }
  ]
}
```
