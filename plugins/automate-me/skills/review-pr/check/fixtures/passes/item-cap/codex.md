Synthetic stand-in for a codex pass. The cap rejects 5.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "within_cap(5)", "broke": true, "observed": "False"},
    {"input": "within_cap(4)", "broke": false, "observed": "True"}
  ],
  "findings": [
    {
      "file": "head/cap.py",
      "line": 3,
      "claim": "within_cap(5) returns False, so a full list of 5 is rejected.",
      "repro": "within_cap(5)"
    }
  ]
}
```
