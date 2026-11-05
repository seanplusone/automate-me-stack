# plan.json shape

```json
{
  "title": "Weekly digest email",
  "ask": {"quote": "The user's words, as written", "source": "chat 2026-11-04"},
  "outcome": {
    "outcome": "What exists at the end that doesn't now.",
    "done_when": "A check an agent can run.",
    "limits": "What not to touch; how big it can get."
  },
  "big_picture": "At most 3 sentences. The problem, then what the plan builds.",
  "items": [
    {
      "id": "A",
      "name": "Find who opens the current alerts",
      "plain": "One sentence anyone can read, PM or junior engineer.",
      "after": [],
      "only_if": "",
      "size": "S",
      "spec": {
        "outcome": "One sentence.",
        "done_when": "A check an agent can run or see.",
        "limits": "What the agent must not touch.",
        "output": "What comes back, and where it is saved.",
        "harness": "findings file",
        "loop": {"max": 3, "exit_when": "The harness passes, or the cap is hit and the agent reports what failed."},
        "verifier": "A fresh agent reruns the harness and reads the diff.",
        "tools": ["read-only database query", "shell"],
        "model": "sonnet",
        "effort": "medium",
        "context": ["plan.json item A", "the mail log schema"]
      },
      "decisions": [
        {"choice": "Count opens from the mail log.", "over": ["Ask the PM"], "because": "The log has 90 days of opens.", "label": "guess"}
      ],
      "open": ["A question only the user can answer, with a suggested answer."]
    }
  ],
  "patterns": {"fired": ["sync"], "not_fired": ["import"]},
  "gaps": [
    {"text": "A sync that looks like a reload could overwrite every record.", "from": "rule:sync", "owner": "engineer", "changes": "A"}
  ],
  "log": [
    {"item": "A", "challenge": "Why not ask the PM?", "answer": "held", "because": "One sentence with its evidence."}
  ],
  "legend": {"digest": "One email that groups a week of alerts."}
}
```

## Rules the checker enforces

- `items`: 1 to 8. More than 8 means the idea is two projects; split the ask.
- `id`: one capital letter, unique. `after` names only earlier ids, so the order has no cycle.
- `only_if`: optional. The result of an earlier item that makes this one needed.
- `spec.tools`: at least one. `spec.model`: the model or role that runs it. `spec.effort`: `low`, `medium`, `high` or `xhigh`. `spec.context`: the only files and outputs the agent gets.
- Prose: at most 900 words, and at most 2 `open` questions across all items.
- `size`: `S` or `M`. An `L` item must be split before the page goes out.
- `plain`, `spec.outcome`: one sentence each. `big_picture`: 1 to 3 sentences.
- `spec.harness`: a kind from `../../shared/harness-kinds.md`.
- `spec.loop.max`: a whole number from 1 to 10. `exit_when` says what happens when the cap is hit.
- `decisions[].label` and nothing else carries certainty: `measured`, `inferred` or `guess`. `over` names at least one rejected option.
- `patterns`: every engineering rule file (shared/rules/eng), listed as `fired` or `not_fired`. Empty lists when that folder has no files.
- `gaps`: at most 8, at most 250 words, outside the 900. Each is one sentence. `from` is `rule:<fired set>`, `evidence` or `guess`. `owner` is `pm` or `engineer`. `changes` names an item, or says `question`.
- `log[].answer`: `held` or `changed`. A `changed` entry means the item above it was edited.
- Every legend term appears on the page. The writing rules in `../../shared/writing-rules.md` apply to all prose.
