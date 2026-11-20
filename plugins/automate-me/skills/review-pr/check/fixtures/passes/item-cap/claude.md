Synthetic stand-in for a claude pass. Same bug, a shorter path.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "within_cap(5)", "broke": true, "observed": "False"},
    {"input": "within_cap(4)", "broke": false, "observed": "True"}
  ],
  "findings": [
    {
      "file": "cap.py",
      "line": 3,
      "claim": "The comparison is less-than, so 5 falls outside a cap of 5.",
      "repro": "call within_cap on 5"
    }
  ]
}
```
