---
name: outcome
description: Turn a rough idea, often a spoken ramble or a voice transcript, into a brief an agent can run. Sorts what was said into decisions, thinking aloud, tangents, questions and facts. Then it fills brief-check's slots and marks every gap unknown with the one question that fills it. It reads the brief back with at most 3 questions. Nothing runs until the user says yes. Use for /outcome, "here's a rough idea", "I'm just thinking out loud", or a long unstructured message about building, reviewing, designing, learning or deciding something. When a message looks like a ramble, offer it in one line first.
---

# Outcome

A rough idea arrives as a ramble. It mixes firm decisions with "maybe", drifts into tangents, and leaves the most important limits unsaid. This skill turns it into a brief with the shape of a prompt that works for an agent. It never fills a gap with a guess.

Voice is only how the text arrives. The skill works on the transcript, typos and all.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## When to offer it

The user can type `/automate-me:outcome`. A message may be a long ramble with no clear ask. Then offer it in one line: "Want me to turn this into a brief first?" Without a yes, answer the message as usual. With a yes, the skill shows the read-back and stops there. Nothing else runs until the user says yes to the brief.

## Kinds of rough idea

Name the kind in the brief's `Kind` slot. It changes what Output and Verify look like. The second table lists limits to check for every brief of that kind, even when the speaker never mentions them. If the ramble doesn't settle one, it becomes an unknown.

| Kind | One-line example | Output and Verify lean on |
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
| Fact | Names, numbers, links, files | "2600", "Irvine", "the PRD in the shared folder" |

Keep the speaker's own words for every number and name. Never round, convert or "fix" them. If they said "5k", write "5k". If they gave two numbers, do not add them up and call the sum a limit.

How each pile lands in the brief:

- **Self-correction.** "Actually X" or "no wait, X" replaces what came before. Keep only the corrected version. Do not keep both.
- **Decision.** It becomes a must-have or a taste item.
- **Thinking aloud.** If the work can start on it and a wrong guess is cheap to fix, keep it as an item and end it with "(hedged, confirm)". If the answer changes the shape of the work (a table, a cap, the scope), it becomes an unknown. It is never a plain must-have.
- **Tangent.** It goes to the Parking lot and is not acted on.
- **Question the agent can answer by looking.** Examples are "does the PRD cover annual plans?" or "why does an index help?". It becomes a Must-haves item `investigate: <question>`.
- **Question only the user can answer.** Examples are "can a dog have two owners?" or "is 5k the cap?". It becomes an unknown.
- **Exclusion.** "Not now" or "skip X" becomes a Must-haves item `out of scope: <X>`. If it is an idea for later ("maybe later"), it also goes to the Parking lot so it is not lost.
- **Process ask.** "Do them in parallel", "one agent per source" or "have someone double check" each have a slot. How the work is split goes in Skills as `how: <...>`. A second checker goes in Verify. "Report only" goes in If stuck.

## 2. Fill the brief

Use the slots defined in [brief-check](../brief-check/SKILL.md), Step 1. Read them there; this skill does not restate them. The brief adds four slots of its own: Kind, Skills, Parking lot and Unknowns. Decision is split out of Goal so it can be marked unknown on its own line.

Write the brief to a file in the session's scratch folder, one line per slot. Use the labels exactly as the template shows them. A note in brackets after a label, as in `- Taste (flag, don't filter):`, is allowed. Every slot except Kind is required.

```
# Brief: <short title>

- Kind: build | review | design | learn | search/decide
- Plan first: yes: <what the plan shows first> | none needed
- Goal: <what to do>
- Decision: <what the user will decide with the result>
- Context: <what exists: repo, files, links, prior decisions>
- Must-haves:
  - <checkable rule, with its named proof>
  - investigate: <a question the agent answers by looking>
  - out of scope: <what the speaker excluded>
- Taste: <preferences, each "flag, don't filter", with its visible signal>
- Output: <what comes back, how many, which fields>
- Verify: <how each claim is proved; every claim names its run, file:line or photo, or says guess>
- If stuck: <stop rule, loop cap, never loosen a must-have without asking, report only>
- Skills:
  - <skills to call later; none run yet>
  - how: <how the work is split, e.g. in parallel>
- Parking lot: <tangents, not acted on>
- Unknowns:
  - unknown: <the one question that fills it>?

## Questions

1. <question>?
```

A slot with more than one item puts each on its own indented `  - ` line.

Plan first is the agent's call, never a question for the user. Write `yes: <what the plan shows>` when the work is big, runs many agents, or costs real time or money. Write `none needed` when it is one pass the user can redo cheaply.

Skills: propose skills that fit, from this plugin or the user's own. Examples: review-prd or review-prd-light for a PRD, review-pr for a PR, explain-doc for a long doc, write-edd for a design, decode-ask for a colleague's message. Do not run any of them yet. If the speaker wants what worked saved, say so here too; the Learn section below has the steps.

## 3. Mark unknowns, never guess

A slot the speaker did not fill is written `unknown: <the one question that fills it>?`. List every unknown again under Unknowns. A gap filled with a plausible guess is worse than an honest unknown, because nobody checks a guess.

Never offer a default next to an unknown ("unknown: which fields? Default: link and price"). A default is a guess the user has to catch. Leave the unknown on its own. The agent may say what it does until the answer comes, but only when that changes no result, for example "lists what the photos show and does not rate it".

Then check the "Check even if unsaid" table for the brief's kind. Each limit there that the ramble does not settle becomes an unknown.

Then apply brief-check's trap list (Step 2) to the brief, one line per trap found:

- An adjective with no proof (modern, clean, good, correct) becomes the visible signal that shows it, or an unknown asking for one.
- Unknown treated as no: a rule answers yes, no or unknown, and unknown is flagged, not dropped.
- Taste is "flag, don't filter". Only a decision stated firmly becomes a must-have.
- Side effects (post, message, apply, edit, buy) get "report only" in If stuck unless the user asked for the action.
- Vague scope ("the PRD", "the repo") names a link, path or branch, or becomes an unknown.
- A check that needs a tool (a browser, images, a test run) names it.

Run `python3 "$SKILL_DIR"/check/check_brief.py <brief.md>` and fix what it flags. It checks the shape. Every slot is present once and filled, and Plan first says yes or none needed. Every unknown has a question and no default beside it. Tagged items sit in their slots, there are at most 3 questions, and no slot is only an adjective. Run `python3 "$SKILL_DIR"/../shared/check_writing.py <brief.md>` and rewrite the lines it flags.

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
2. Score the final brief with brief-check (Step 1 table and Step 2 traps).
3. Run it, or the proposed skills, per brief-check Step 3. A gap only the user can fill still stops the run.

For parallel work, brief each subagent with one part of the brief and the same Verify and If stuck lines. A second agent that did not do the work checks it before the results come back.

## Iterate

A later message often changes the ask: "actually carpet only in bedrooms", "peek the next 100 up". Update the brief in place. Show only the lines that changed, marked old and new, and rerun the brief check. Do not rebuild the whole brief or re-ask questions already answered.

## Learn

When a run teaches something, offer once to save it. Examples are a filter that dropped good results, or a better proof source (photos over descriptions). Use the steps in [learn-from-run](../shared/playbooks/learn-from-run.md). A person approves each saved rule. A one-off fact stays out of shared rules and goes to the user's own notes, if they want it kept.

## Why

A spoken idea holds the goal, but the limits come out half-said ("we can go up to 5k if it's really good"). The tangents sound as firm as the decisions. An agent handed the raw ramble guesses the missing limits and acts on the tangents. Sorting first, then marking gaps as questions, makes the user's answers the only source for what was left unsaid.
