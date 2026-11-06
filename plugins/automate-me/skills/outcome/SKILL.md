---
name: outcome
description: Turn a rough idea, often a spoken ramble or a voice transcript, into a brief an agent can run. Sorts what was said into decisions, thinking aloud, tangents, questions and facts, then fills brief-check's slots, marks every gap unknown with the one question that fills it, and reads the brief back with at most 3 questions. Nothing runs until the user says yes. Use for /outcome, "here's a rough idea", "I'm just thinking out loud", or a long unstructured message about building, reviewing, designing, learning or deciding something. When a message looks like a ramble, offer it in one line first.
---

# Outcome

A rough idea arrives as a ramble. It mixes firm decisions with "maybe", drifts into tangents, and leaves the most important limits unsaid. This skill turns it into a brief with the shape of a prompt that works for an agent. It never fills a gap with a guess.

Voice is only how the text arrives. The skill works on the transcript, typos and all.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## When to offer it

The user can type `/automate-me:outcome`. When a message is a long ramble with no clear ask, offer it in one line: "Want me to turn this into a brief first?" Without a yes, answer the message as usual. With a yes, the skill shows the read-back and stops there. Nothing else runs until the user says yes to the brief.

## Kinds of rough idea

Name the kind in the brief's `Kind` slot. It changes what Output and Verify look like.

| Kind | One-line example | Output and Verify lean on |
|---|---|---|
| build | "sketch an ERD for the booking app" | a diagram or code, checked against the named entities and rules |
| review | "go through this PRD, find the holes" | gaps and questions, each tied to a section or line |
| design | "think through how the sync job should scale" | options with tradeoffs, each claim tied to the code or a run |
| learn | "help me understand how indexes work" | an explanation plus a short check of understanding, every source cited |
| search/decide | "find me a 3 bed apartment under budget" | a ranked list with fields, every claim backed by a listing or a photo |

## 1. Sort what was said

Read the whole input before writing anything. Put every sentence in one of five piles:

| Pile | What it is | Example |
|---|---|---|
| Decision | Stated firmly | "carpet only in the bedrooms is fine" |
| Thinking aloud | Hedged: "maybe", "I guess", "kind of" | "maybe reviews later" |
| Tangent | Off the goal | "the pricing page is a mess too" |
| Question | Something the speaker asked | "can a dog have two owners?" |
| Fact | Names, numbers, links, files | "2600", "Irvine", "the PRD in the shared folder" |

Keep the speaker's own words for every number and name. Never round, convert or "fix" them. If they said "5k", write "5k". If they gave two numbers, do not add them up and call the sum a limit.

A decision becomes a must-have or a taste item. Thinking aloud becomes a taste item or an unknown, never a must-have. A tangent goes to the Parking lot and is not acted on. A question the speaker raised stays a question; it becomes an unknown or one of the read-back questions.

## 2. Fill the brief

Use the slots defined in [brief-check](../brief-check/SKILL.md), Step 1. Read them there; this skill does not restate them. The brief adds four slots of its own: Kind, Skills, Parking lot and Unknowns. Decision is split out of Goal so it can be marked unknown on its own line.

Write the brief to a file in the session's scratch folder, one line per slot, in this shape:

```
# Brief: <short title>

- Kind: build | review | design | learn | search/decide
- Plan first: <only for a big or ambiguous task>
- Goal: <what to do>
- Decision: <what the user will decide with the result>
- Context: <what exists: repo, files, links, prior decisions>
- Must-haves: <checkable rules, each with its named proof>
- Taste: <preferences, each "flag, don't filter", with its visible signal>
- Output: <what comes back, how many, which fields>
- Verify: <how each claim is proved; every claim names its run, file:line or photo, or says guess>
- If stuck: <stop rule, loop cap, never loosen a must-have without asking>
- Skills: <skills to call later; none run yet>
- Parking lot: <tangents, not acted on>
- Unknowns:
  - unknown: <the one question that fills it>?

## Questions

1. <question>?
```

A slot with more than one item puts each on its own indented `  - ` line.

Skills: propose skills that fit, from this plugin or the user's own. Examples: review-prd or review-prd-light for a PRD, review-pr for a PR, explain-doc for a long doc, write-edd for a design, decode-ask for a colleague's message. Do not run any of them yet.

## 3. Mark unknowns, never guess

A slot the speaker did not fill is written `unknown: <the one question that fills it>?`. List every unknown again under Unknowns. A gap filled with a plausible guess is worse than an honest unknown, because nobody checks a guess.

Then apply brief-check's trap list (Step 2) to the brief, one line per trap found:

- An adjective with no proof (modern, clean, good, correct) becomes the visible signal that shows it, or an unknown asking for one.
- Unknown treated as no: a rule answers yes, no or unknown, and unknown is flagged, not dropped.
- Taste is "flag, don't filter". Only a decision stated firmly becomes a must-have.
- Side effects (post, message, apply, edit, buy) get "report only" unless the user asked for the action.
- Vague scope ("the PRD", "the repo") names a link, path or branch, or becomes an unknown.
- A check that needs a tool (a browser, images, a test run) names it.

Run `python3 "$SKILL_DIR"/check/check_brief.py <brief.md>` and fix what it flags. It checks the shape: every slot present once and filled, every unknown with a question, at most 3 questions, and no slot that is only an adjective. Run `python3 "$SKILL_DIR"/../shared/check_writing.py <brief.md>` and rewrite the lines it flags.

## 4. Read back

Show the brief, one line per slot. Under it, ask at most 3 numbered questions. Ask only what nobody but the user can answer:

- which decision the result is for;
- scope: which files, links, area or set;
- limits: budget, caps, deadlines;
- anything that would make the agent guess at intent.

Other unknowns stay listed in the brief. The agent reports them in its output and does not guess them. End with "Say yes, or answer the questions, and I'll run it."

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
