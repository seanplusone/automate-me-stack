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
      "plain": "Count who opens the daily alerts today, so the digest has a baseline.",
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
  "patterns": {"fired": [], "not_fired": []},
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
- `gaps`: at most 8, at most 250 words, outside the 900. Each is one sentence. `from` is `rule:<set>`, `evidence` or `guess`. The set is a fired engineering set, or a PM set in `../../shared/rules/` such as `rule:sync`. `owner` is `pm` or `engineer`. `changes` names an item, or says `question`.
- `log[].answer`: `held` or `changed`. A `changed` entry means the item above it was edited.
- Every string that lands in a prompt follows outcome's placeholder rule (`../outcome/check/check_brief.py`): `title`, `outcome.outcome`, and each item's `name`, `only_if`, `spec.outcome`, `done_when`, `output`, `limits`, `verifier`, `model`, `loop.exit_when`, `tools` and `context`. So do `outcome.done_when` and `limits`. Each is one line of text. A placeholder or template hole fails. A value that needs a person prints `ASK: <field>: Is '<value>' a real answer for <field>?` and exits 2. Ask the person. On a yes, add it to an optional top-level `"confirmed"` map, keyed by the field as the ASK line names it, as `{"item A spec.output": "ok"}`, and rerun. On a no, rewrite the field. `render_plan.py --prompt` copies each prompt slot that carries a confirmed field into the prompt's `## Confirmed` block. When the fields pass, each rendered prompt must pass check_brief too.
- Every legend term appears on the page. The writing rules in `../../shared/writing-rules.md` apply to all prose.
