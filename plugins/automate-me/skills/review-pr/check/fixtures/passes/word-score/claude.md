Synthetic stand-in for a claude pass. Same line, a head prefix.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "bug line bug line", "broke": true, "observed": "True"},
    {"input": "all good", "broke": false, "observed": "False"}
  ],
  "findings": [
    {
      "file": "head/score_review.py",
      "line": 6,
      "claim": "Keyword stuffing with bug and line is scored as a pass.",
      "repro": "bug line bug line"
    }
  ]
}
```
