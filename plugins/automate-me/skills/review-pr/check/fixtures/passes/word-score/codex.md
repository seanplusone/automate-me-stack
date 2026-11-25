Synthetic stand-in for a codex pass. Keyword stuffing scores as a pass.

```json
{
  "verdict": "needs fixes",
  "tried": [
    {"input": "bug line bug line", "broke": true, "observed": "True"},
    {"input": "all good", "broke": false, "observed": "False"}
  ],
  "findings": [
    {
      "file": "score_review.py",
      "line": 6,
      "claim": "passes returns True for the text bug line bug line, which names no defect.",
      "repro": "bug line bug line"
    }
  ]
}
```
