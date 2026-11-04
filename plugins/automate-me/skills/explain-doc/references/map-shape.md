# The map file

One JSON file per doc. `check/check_map.py` validates it and `check/render_page.py` turns it into the page. Optional keys may be left out.

```json
{
  "title": "Example Billing Migration",
  "source": {"path": "docs/design/example-billing-migration.md", "version": "read at 1111111, file last changed 2222222", "link": "https://..."},
  "status": "Optional. One or two sentences when the source's own status is out of date, e.g. it says draft but the code shipped on 1 Jan 2030 (commit 3333333).",
  "big_picture": "At most five sentences. The problem through the example first, then what the doc changes.",
  "example": "Optional. Two to four sentences that set up the example (A, B, C) once. Shown before the big picture.",
  "decisions": [
    {"question": "Should a contractor see site notes?", "why": "One sentence.", "lines": "1250"}
  ],
  "flow": {
    "title": "One sync, in three stages",
    "intro": "Optional. One sentence, e.g. where it can stop.",
    "stages": [
      {"name": "Read", "text": "One or two sentences.",
       "table": {"head": ["If this is true", "The sync", "Who acts"], "rows": [["...", "...", "..."]]},
       "note": "Optional. One sentence under the table."}
    ],
    "source_lines": "107-223"
  },
  "states": [
    {"title": "A record's states", "names": ["Active", "Removed", "Deleted forever"],
     "rows": [["Active to Removed", "An admin presses Remove"], ["Removed to Active", "An admin presses Restore"]],
     "note": "Optional."}
  ],
  "sections": [
    {"name": "Motivation", "lines": "25-36", "summary": "One or two sentences.", "points": ["At most four, one sentence each."]},
    {"name": "The endpoint (code PR)", "files": ["app/Http/Controllers/X.php"], "summary": "...", "points": []}
  ],
  "tables": [
    {"title": "What the database gains", "intro": "Optional.", "head": ["Where", "What it holds"], "rows": [["...", "..."]]}
  ],
  "wrong": [
    {"text": "One or two sentences.", "lines": "33, 942", "label": "measured"}
  ],
  "legend": {"term": "One plain sentence."}
}
```

Limits the check enforces:
- `big_picture`: 1 to 5 sentences.
- `flow.stages`: 1 to 5, each with 1 to 3 sentences of `text`. A stage table has a header and every row has as many cells as the header.
- `sections`: 1 to 15. Each has `lines` (like `25-36` or `25`), or `files` for a code PR, a summary of 1 to 2 sentences and at most 4 points.
- `decisions`: each has a `question` and `lines`.
- `states`: one entry or a list. Each has at least two names, and every row is [change, who or what does it].
- The page's prose: at most 2,500 words.
- `wrong`: at most 10. Each has `lines` (or `files`), 1 to 3 sentences and a `label` of measured, inferred or guess.
- `legend`: at least one term, and every term is used somewhere on the page. The hover matches the term case-insensitively, plus a plural, "-ed", "-d" or "-ing" ending, on its first use in each block.
- All prose, stage and section names, and legend definitions pass `../shared/check_writing.py` (relative to the explain-doc folder).
