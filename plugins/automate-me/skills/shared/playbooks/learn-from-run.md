# Playbook: Learn from a run

Turn misses and corrections into rules, so the same miss does not happen twice. The AI proposes. A person approves every change.

Adapted from pstack's `reflect` skill and its "encode lessons in structure" principle, and from Cursor's `continual-learning` plugin (both MIT). Unlike `continual-learning`, nothing is written without approval, because rule files that grow on their own fill with noise.

Copy these steps into the todolist word for word.

## When to run

Any of these:
- A scored test run missed an item in its key.
- The person added a question, a hazard or a rule by hand during a review.
- Answers came back, from a PM or any other reviewer, and reveal something nobody asked.
- A panel check kept a finding that a rule or check could have caught earlier.

## Steps

1. **Collect.** List each miss or correction, with its source: the run, the input document (PRD, ticket, design doc or PR), the answer or the panel finding.
2. **Propose.** For each one, draft the smallest change that would have caught it:
   - A question in an existing rule file.
   - A new shape rule file, only if no existing file fits and the pattern has appeared at least twice.
   - A writing rule with one bad and one good example.
   - A step or check in a skill.
   - A line in the project's capability index or jargon list. These live in the project repo, not here.
3. **Filter.** Keep a proposal only if it passes all of these:
   - Durable: still true in 6 months. No file paths, versions or one-off facts in a shared rule.
   - Specific: a future run would recognize when to apply it. Not "be careful".
   - Decision-changing: a future run does something different because of it.
   - Not already covered: read the target file first. If the rule exists and was ignored, the fix is wording or placement, not a duplicate.
   - Repeated: a new shape file needs the pattern at least twice. A single miss can still add one question to an existing file.
4. **Structure first.** If a script check can enforce it, make it a check, not prose. Prose is for what a script cannot judge.
5. **Show the person.** Present three lists:
   ```
   ACCEPT | <problem> | <proposed change> | <target file>
   REJECT | <proposal> | <reason>
   BACKLOG | <proposal that needs a check written> | <target>
   ```
6. **Apply only what the person approves.** Re-run the affected checks after each change.

## Guards

- Never edit rules, skills or checks without approval.
- Project-specific facts go to the project repo. Shared files stay generic.
