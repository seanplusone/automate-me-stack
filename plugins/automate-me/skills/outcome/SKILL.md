---
name: outcome
description: Turn a rough idea, often a spoken ramble or a voice transcript, into a brief an agent can run. Sorts what was said into decisions, thinking aloud, tangents, questions and facts. Then it fills the brief slots and marks every gap unknown with the one question that fills it. It reads the brief back with at most 3 questions. Nothing runs until the user says yes. Use for /outcome, "here's a rough idea", "I'm just thinking out loud", or a long unstructured message about building, reviewing, designing, learning or deciding something. When a message looks like a ramble, offer it in one line first. A shape-idea decisions.md is mapped into the brief before the read-back.
---

# Outcome

A rough idea arrives as a ramble. It mixes firm decisions with "maybe", drifts into tangents, and leaves the most important limits unsaid. This skill turns it into a brief with the shape of a prompt that works for an agent. It never fills a gap with a guess.

Voice is only how the text arrives. The skill works on the transcript, typos and all.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. The same steps apply on any stack and for any coding agent.

## A decisions file

If the user brings a `decisions.md` from [shape-idea](../shape-idea/SKILL.md), run `python3 "$SKILL_DIR"/../shape-idea/check/check_decisions.py` on that file first. If it fails (exit 1), stop and show the failures. Do not map a file the check rejects. Exit 2 is a break point. Stop, ask the user each `ASK:` line as a yes/no question, and record the answer in the decisions file. A yes is a `- <Slot>: <value>` line under `## Confirmed` at its end. A no is a new value. Run the check again. Map only on exit 0. Do not sort it as a ramble. Shape-idea does not ask which tool to use, who does the work, or which two cases prove it. Those three stay `unknown:` until the user answers, unless a Decided line already names that slot. Do not invent them. Run `python3 "$SKILL_DIR"/check/check_brief.py` on the brief.

| In the decisions file | In the brief |
|---|---|
| The `goal:` line | Goal |
| The `done:` line | Done |
| A decided `out of scope:` line | Constraints |
| A decided `decide:` line | Goal, in place of the decide question |
| Other Decided lines | Done |
| A decided `output:` line | Output |
| An open slot | That slot as `unknown:`, and again under Unknowns |
| The `constraints:` line | Constraints |
| A Parked `out of scope:` line, or one that ends in not now, `, later` or `for later` | Constraints as `out of scope:`, and the Parking lot |
| A Parked question | Unknowns as `unknown: <question>?`, and the Parking lot |
| Other Parked lines | Parking lot |
| The `verify:` line | Verification, plus the evidence sentence |
| A decided `tools:`, `agents:`, or `evals:` line | That slot, in the user's words |
| Tools, Agents and roles, and Evals when unset | Unknowns |
| The Confirmed section | The brief's `## Confirmed` block |

A Parked line becomes `out of scope:` when it is tagged `out of scope:`, or ends in not now, `, later` or `for later`. A later inside double quotes does not count. A later in the middle of a line, as in "voters who join later can still vote", keeps its meaning and stays parked. So does a later hedged with maybe, perhaps, probably, possibly, I think, or not sure, a line that ends in `?`, and a line the brief check would not pass as written. A tagged line keeps one `out of scope:`. A parked question stays a question.

Goal also gets `unknown: What will you decide with the result?` unless a Decided line starts with `decide:`. That line's value goes under Goal instead, with no `decide:` in front, as the template writes it. Tools is `unknown: Which tool must the run use, and what, if anything, must be written first?`. Agents and roles is `unknown: Who does the work, and does anyone else check it?`. Evals is `unknown: What is one case that should pass, and one that should fail?`. A decided `tools:`, `agents:` (or `agents and roles:`), or `evals:` line fills that slot instead. An Open `tools:`, `agents:`, `evals:` or `decide:` question takes the stock question's place. A decided `write first:` line goes under Tools. After the user answers, rewrite each slot in their words.

Some lines start with a brief tag outside its home slot, or with `default`. When such a line is a Decided line that is not a slot, or a Parked line, it is prefixed with `stated:`. The words stay and the tag does not. A slot value is never prefixed. `stated:` never hides an unknown, a trap word, a placeholder or an ask: the decisions check judges every line without it, and fails or asks first.

The read-back asks at most 3 questions, in this order: an open goal or done question, then the decide question, then Tools, then Agents and roles, then Evals. Unasked ones stay in Unknowns. Constraints also says report only, and not to run or post, because shape-idea never does. The same traps apply.

## When to offer it

The user can type `/automate-me:outcome`. A message may be a long ramble with no clear ask. Then offer it in one line: "Want me to turn this into a brief first?" Without a yes, answer the message as usual. With a yes, the skill shows the read-back and stops there. Nothing else runs until the user says yes to the brief.

## Kinds of rough idea

Name the kind in the brief's `Kind` slot when you can tell it. Kind is optional. It changes what Output, Evals and Verification look like. The second table lists limits to check for every brief of that kind, even when the speaker never mentions them. If the ramble doesn't settle one, it becomes an unknown.

| Kind | One-line example | Output and Verification lean on |
|---|---|---|
| build | "sketch an ERD for the booking app" | a diagram or code, checked against the named entities and rules |
| review | "go through this PRD, find the holes" | gaps and questions, each tied to a section or line |
| design | "think through how the sync job should scale" | options with tradeoffs, each claim tied to the code or a run |
| learn | "help me understand how indexes work" | an explanation plus a short check of understanding, every source cited |
| search/decide | "find me a 3 bed apartment under budget" | a ranked list with fields, every claim backed by a listing or a photo |

Check even if unsaid:

| Kind | Limits |
|---|---|
| build | scale, who owns each part, what already exists |
| review | deadline, who reads it, how many items at most |
| design | load, hard constraints such as cost or stack, who decides |
| learn | version, data size, where an example may run |
| search/decide | timing, location or scope, hard cap versus target |

## 1. Sort what was said

Read the whole input before writing anything. Put every sentence in one of five piles:

| Pile | What it is | Example |
|---|---|---|
| Decision | Stated firmly | "carpet only in the bedrooms is fine" |
| Thinking aloud | Hedged: "maybe", "I think", "kind of" | "maybe reviews later" |
| Tangent | Off the goal | "the pricing page is a mess too" |
| Question | Something the speaker asked | "can a dog have two owners?" |
| Fact | Names, numbers, links, files | "2600", "Riverton", "the PRD in the shared folder" |

Keep the speaker's own words for every number and name. Never round, convert or "fix" them. If they said "5k", write "5k". If they gave two numbers, do not add them up and call the sum a limit.

How each pile lands in the brief:

- **Self-correction.** "Actually X" or "no wait, X" replaces what came before. Keep only the corrected version. Do not keep both.
- **Decision.** A firm rule becomes a Done item. What the result is for goes on its own line under Goal, so it can be marked unknown without losing the rest of the goal.
- **Thinking aloud.** If the work can start on it and a wrong guess is cheap to fix, keep it as an item and end it with "(hedged, confirm)". If the answer changes the shape of the work (a table, a cap, the scope), it becomes an unknown. It is never a plain Done item.
- **Tangent.** It goes to the Parking lot and is not acted on.
- **Question the agent can answer by looking.** Examples are "does the PRD cover annual plans?" or "why does an index help?". It becomes a Done item `investigate: <question>`.
- **Question only the user can answer.** Examples are "can a dog have two owners?" or "is 5k the cap?". It becomes an unknown.
- **Exclusion.** "Not now" or "skip X" becomes a Constraints item `out of scope: <X>`. If it is an idea for later ("maybe later"), it also goes to the Parking lot so it is not lost.
- **Process ask.** "Do them in parallel", "one agent per source" or "have someone double check" each have a slot. How the work is split goes in Agents and roles as `how: <...>`. A second checker goes in Verification, and the role is named again under Agents and roles. "Report only" goes in Constraints.

## 2. Fill the brief

Done is the criteria. Evals are the cases that show those criteria hold. Verification is how each claim in the result is proved. Do not collapse the three into one line.

These slots are required. A brief that omits any one of them fails the checker:

| Slot | What it holds |
|---|---|
| Goal | What to do. The decision the result is for goes on its own line, or `unknown: <question>?` when unsaid. |
| Done | Specific, observable criteria. Each one names its proof. |
| Output | What comes back, how many, which fields, and how the person wants to see it. |
| Constraints | Guardrails. Stop rule, loop cap, report only, and what is out of scope. |
| Tools | Tools the run needs, and what must be written before the run starts. |
| Agents and roles | Who does the work, who checks it, and how the work is split. |
| Evals | One case that should pass and one that should fail. |
| Verification | How each claim is proved. Every claim names its run, file:line or photo, or says guess. |

These slots are optional. Write one when the ramble gives you something to put there. Omit it when it would only say none:

| Slot | What it holds |
|---|---|
| Kind | build, review, design, learn, or search/decide. |
| Plan first | The agent's call. `yes: <what the plan shows>` or `none needed`. Never a question for the user. |
| Taste | Preferences. Each one is "flag, don't filter", with the visible signal that shows it. |
| Skills | Skills to call later. None run yet. |
| Parking lot | Tangents. Not acted on. |
| Unknowns | Every unknown, repeated, each as `unknown: <question>?`. |

Write `yes` for Plan first when the work is big, runs many agents, or costs real time or money. Write `none needed` when it is one pass the user can redo cheaply.

Tools names every tool a check needs, and says to check that the tool works first. It also says what must be written before the run, as `write first: <what>`, or `write first: none` next to the tool name. `write first: none` by itself does not fill the slot. If there is no tool, write `none: <why>`. A breakdown prompt uses `Waits for:` for the items that must finish first. That is not the `write first:` line. The plan itself stays in Plan first.

For Output, ask: "Where will this live, and what shares that space (container, overlays, states)?" An unknown answer is written `unknown: <question>?` and asks the person.

Evals name a concrete pass and a concrete fail. An eval is not a restatement of Done with no example.

Skills: propose skills that fit, from this plugin or the user's own. Examples: review-prd or review-prd-light for a PRD, review-pr for a PR, explain-doc for a long doc, write-edd for a design, decode-ask for a colleague's message. Do not run any of them yet. If the speaker wants what worked saved, say so here too. The Learn section below has the steps.

The traps in section 3 come from [brief-check](../brief-check/SKILL.md), Step 2. The slot names in this file are the ones the checker enforces. brief-check's own six names are not this brief's required set.

Write the brief to a file in the session's scratch folder. Use the labels exactly as the template shows them. A note in brackets after a label, as in `- Taste (flag, don't filter):`, is allowed.

```
# Brief: <short title>

- Kind: build | review | design | learn | search/decide
- Plan first: yes: <what the plan shows first> | none needed
- Goal: <what to do>
  - <what the person will decide with the result, or unknown: <question>?>
- Done:
  - <observable criterion, with its named proof>
  - investigate: <a question the agent answers by looking>
- Taste: <preferences, each "flag, don't filter", with its visible signal>
- Output: <what comes back, how many, which fields, and how the person sees it>
- Constraints:
  - <stop rule, loop cap, never loosen a done line without asking, report only>
  - out of scope: <what the speaker excluded>
- Tools:
  - <tool the run needs; check it works first>
  - write first: <what must be written before the run, or none>
- Agents and roles:
  - <who does the work, and who checks it>
  - how: <how the work is split, e.g. in parallel>
- Evals:
  - Pass: <one case that meets Done>
  - Fail: <one case that does not>
- Verification: <how each claim is proved; every claim names its run, file:line or photo, or says guess>
- Skills:
  - <skills to call later; none run yet>
- Parking lot: <tangents, not acted on>
- Unknowns:
  - unknown: <the one question that fills it>?

## Questions

1. <question>?
```

A slot with more than one item puts each on its own indented `  - ` line. Kind, Plan first, Taste, Skills, Parking lot and Unknowns may be left out. The eight required slots may not.

## 3. Mark unknowns, never guess

A slot the speaker did not fill is written `unknown: <the one question that fills it>?`. When you write an Unknowns slot, list every unknown there again. A gap filled with a plausible guess is worse than an honest unknown, because nobody checks a guess.

Never offer a default next to an unknown ("unknown: which fields? Default: link and price"). A default is a guess the user has to catch. Leave the unknown on its own. The agent may say what it does until the answer comes, but only when that changes no result, for example "lists what the photos show and does not rate it".

Then check the "Check even if unsaid" table for the brief's kind. Each limit there that the ramble does not settle becomes an unknown.

Then apply brief-check's trap list (Step 2) to the brief, one line per trap found:

- An adjective with no proof (modern, clean, good, correct) becomes the visible signal that shows it, or an unknown asking for one.
- Unknown treated as no: a rule answers yes, no or unknown, and unknown is flagged, not dropped.
- Taste is "flag, don't filter". Only a decision stated firmly becomes a Done item.
- Side effects (post, message, apply, edit, buy) get "report only" in Constraints unless the user asked for the action.
- Vague scope ("the PRD", "the repo") names a link, path or branch, or becomes an unknown.
- A check that needs a tool (a browser, images, a test run) names it in Tools, including what to write first.

Run `python3 "$SKILL_DIR"/check/check_brief.py <brief.md>`. It has three outcomes.

- **Exit 1, FAIL.** Fix what it flags. It flags a missing or repeated slot and an empty slot. It flags any item, or any Evals case, that is a placeholder or a template hole. It also flags a Kind that is not one kind. A placeholder is empty once markup, one tag label and punctuation are stripped, or holds only words from a fixed list, with or without hedge words other than `not`. The words are tbd, tbc, tba, todo, fixme, xxx, n/a, na, none, pending, placeholder and later. The phrases are to be determined, to be decided, to be confirmed, fill in, fill in later, see below, see above and same as above. Spellings such as `T.B.D.`, `to-be-determined` and `TO_BE_DETERMINED` count. A template hole is a value that is nothing but `<goal>`, `{{x}}`, `{x}` or `${x}`. So is a value that holds `[insert x]`, or a line of the template above. The template fails when pasted unfilled. `none` alone may sit on Skills, Parking lot and Unknowns, and beside other items, as in `write first: none`. Tools and Constraints may say `none: <why>` when the reason is real.
- **Exit 2, ASK.** It is in doubt. A value is only hedge words, or only symbols such as `→`, or one word of one or two letters. The hedge words are maybe, perhaps, possibly, probably, not, sure, unsure, unclear, depends, depending, it, idk, dunno, we, ll, will, well, see, yet, tbh, hmm, let and s. A hole inside a longer value, as in `Press <Enter> to submit.`, asks too. It prints `ASK: <slot>: Is '<value>' a real answer for <slot>, or a hole to fill?`. Each other value prints `ASK: <slot>: Is '<value>' a real answer for <slot>?`. Stop there and ask the person that question. On a yes, add a `## Confirmed` block at the end of the brief, with that exact heading. Give it one `- <Slot>: <value>` line for each item or Evals case, and rerun. On a no, replace the value with the answer, or with `unknown: <question>?`. When Evals has content but no pass case or no fail case can be found, it prints `ASK: Evals: Is there a pass case and a fail case here?`. On a yes, label them `Pass:` and `Fail:`. An Evals item `unknown: <question>?` stands in for the cases when its question is in the Questions block.
- **Exit 0, PASS.** The shape is right.

The rule is deliberately narrow. check_brief FAILs only what is unambiguous. When in doubt it ASKs (exit 2, one ASK line each), and the agent stops and asks the person. Asking is cheap, and a wrong FAIL blocks a real brief. The read-back catches the rest.

### Limits

The check is a review aid, not a gate on meaning. It reads wording, so it misses some cases:
- Evals labels in other words, such as `Should pass:` or `Must pass:`, can fail.
- Outline-style Evals, with the case on a nested line under `Pass:`, can fail.
- A short verification command that holds a vague word, such as `make clean`, can be flagged as vague.
- A checklist item such as `[x] TBD` can pass.
- A placeholder with text after it, such as `TBD by Friday`, can pass.

The read-back and the ASK outcome are the backstop.
There are too few real examples to judge wording reliably, so when the check is unsure it asks the person (ASK) rather than deciding.
Save each confirmed answer as a new test case.
As cases build up, more calls can move from asking to automatic, but only after they hold on fresh briefs.

Run `python3 "$SKILL_DIR"/../shared/check_writing.py <brief.md>` and rewrite the lines it flags.

## 4. Read back

Show the brief, one line per slot. Under it, ask at most 3 numbered questions. Ask only what nobody but the user can answer. When more unknowns compete than there are questions, ask the ones that would change the result most, in this order:

1. which decision the result is for;
2. hard limits and scope: budget or cap, dates, area, which files or set;
3. intent: what a vague word means to the user, such as "clean" or "really good".

Related unknowns about one subject may share a question. The rest stay listed under Unknowns. The agent reports them in its output and does not guess them. End with "Say yes, or answer the questions, and I'll run it."

Nothing runs until the user says yes.

## 5. Hand off

After the yes:

1. Fold the answers into the brief. A slot that was unknown now holds the user's words.
2. Run the checker again, and apply the trap list above. Hand off only on exit 0. On exit 2, ask each ASK line's question first and record the answer as above.
3. Run it, or the skills named in the brief. A gap only the user can fill still stops the run, the same rule as brief-check Step 3.

For parallel work, brief each subagent with one part of the brief and the same Verification and Constraints lines. A second agent that did not do the work checks it before the results come back.

## Iterate

A later message often changes the ask: "actually carpet only in bedrooms", "peek the next 100 up". Update the brief in place. Show only the lines that changed, marked old and new, and rerun the brief check. Do not rebuild the whole brief or re-ask questions already answered.

## Learn

When a run teaches something, offer once to save it. Examples are a filter that dropped good results, or a better proof source (photos over descriptions). Use the steps in [learn-from-run](../shared/playbooks/learn-from-run.md). A person approves each saved rule. A one-off fact stays out of shared rules and goes to the user's own notes, if they want it kept.

## Why

A spoken idea holds the goal, but the limits come out half-said ("we can go up to 5k if it's really good"). The tangents sound as firm as the decisions. An agent handed the raw ramble guesses the missing limits and acts on the tangents. Sorting first, then marking gaps as questions, makes the user's answers the only source for what was left unsaid.
