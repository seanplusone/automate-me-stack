# Voice: a non-technical PM

Read before writing anything a PM reads: questions, open-question entries and comments on a PRD. The PM decides what the product does. They do not know how it is built, and they should never need an engineer to understand a question. For review comments to engineers, use `engineer.md` instead.

## The shape

1. **A person at a moment.** A user in one of the product's roles, an admin, or the customer's own team for another system, doing one specific thing.
2. **What they would notice.** What they see, what they can no longer do, or what they lose. Not how the system works.
3. **A choice.** End with the ask. Give the options when there are two or three. Up to three related asks about the same situation can share one question.

One or two sentences of situation, then the ask. Aim for 30 to 40 words. Past 45 words, `review-prd/check/check.py pm-list` fails the question. A one-sentence question is fine when it already names a person and what they notice.

The question carries the decision, not the background. The PM can ask for background in the thread, or read the PRD and the product themselves.

Before, 66 words, from an invented PRD for importing contacts from an external CRM. Every sentence was true, and the PM could not follow it:

> When the same CRM list is connected twice, both connections bring in the same contacts. One part of the PRD keeps them as separate contacts, and another counts a second copy as a duplicate. Should the app keep one copy of each contact, or one per connection? If one copy, which connection's settings decide its details? If one per connection, which copy keeps the order history?

After, 30 words:

> If the same CRM list is connected twice, should each contact appear once in the app, or once per connection? The PRD says both. If once, which connection's settings win?

## Six habits that make a question hard to follow

All six turn up in first drafts of questions for a PM.

**Opening with the engineering plan.** "Before two-way sync can work, we have to change..." makes them read setup before they know what they are being asked. Start with the person.

**Describing how it works.** "Runs on its own", "nothing is locked", "read-only". Say what someone notices: "updates by itself every night", "users can't change it in <product>".

**A word pointing back.** "Should customers see any of that?" makes them reread to find out what "that" is. Pointing at another question fails the same way: "when that happens", "that history". They may read one question alone, so each one stands alone. Name the thing again.

**Stating a guess as a fact.** "We have to change it for every customer" was never in the PRD. If the PRD does not say it, it belongs in the question.

**Packing the setup into one long sentence.** A colon and a list of two changes, then the question, is 35 words before they reach the ask. One idea per sentence.

**Section numbers and requirement IDs.** "§14", "FR16". They have to go and look them up. Describe the part instead: "the PRD's plan for what ships first".

## Three more that pass every check

Each of these can pass the cold reader and the scripts, and the PM still cannot read the question.

**Explaining today's product first.** "Today a contact that both lists include is one contact in the app. It belongs to whichever list imported last." Put a fact about today in only when the ask makes no sense without it. Most of the time, it is the engineer's evidence, and it belongs in the design doc.

**Quoting both sides of the PRD.** Two sentences restating what each part of the PRD says before the ask. When the ask already names both options, "The PRD says both." is enough.

**Asking about a branch they haven't picked.** "If one per connection, which copy keeps the history?" only matters after they pick that option. Ask it then.

## Words to swap

| Instead of | Write |
|---|---|
| sync, syncing | updates between <product> and the customer's <other system> |
| read-only, locked | can't be edited in <product> |
| push, write back | send to the customer's <other system> |
| field, attribute | a detail, such as a record's name |
| table, entity, record | the thing the person knows by name |
| dirty, queued, pending | edits not sent yet |
| conflict | both sides changed the same detail |

The feature's own name, such as "two-way sync", is fine. The PM named it.

Name the product, the customer and each role as the PRD does. In review-prd those names are in `out/terms.txt`. Never use a job title the product has no role for.

## A glossary at the top

A term with no everyday swap is defined once in a short glossary at the top of the list, at most 6 terms. A list that needs no term has no glossary. Use each term the way the glossary defines it.

Name each term in plain words, not with the PRD's label. The PRD may coin a label for its own mechanism, such as a field direction or a status badge. Pick a name the PM would say out loud, and end the entry with "The PRD calls it <label>." The questions then use the plain name only. A label the person will see on screen can appear once in a question as `(the PRD calls it "<label>")`.

## Contradictions in the PRD

When neither side is plainly right, name both in plain words, then ask which is right. "The PRD says the customer's own team turns this on and off. It also says an admin in <product> does. Who should?" When the ask already names the two options, "The PRD says both." is enough.

When one side is plainly right, it is not a question. It can go to the PM as a correction, below.

## Where it goes on the PRD

Engineering adds exactly two things to a PRD. Nothing else is added, removed or changed.

- **Open questions** go in one section added at the very bottom of the PRD they belong to, after everything the PM wrote. It is the block from `review-prd/templates/open-questions.md`, under that template's "Questions from engineering" heading. The PM answers under each question. A question about one child PRD goes on that child page, never on the parent. Open questions are never comments.
- **Corrections to the PRD's logic** go inline, one comment on the line that is wrong. Corrections are never in the bottom section.
- **A linked test plan is its own document.** Its corrections go inline on the test plan page. A missing test case is not a correction, because it has no line. It is a question. Its open questions go in their own section at the bottom of the test plan page, not on the PRD.

Every other line of the PRD stays exactly as the PM wrote it.

## Corrections to the PRD

A correction is a comment on the line it is about, one comment per line.

Say what is off in one sentence, then ask for the change. Aim for 35 words or fewer. Leave out how we found it ("we checked this against the product") and the evidence. The PRD's own labels, such as "R4", are fine here, because the comment sits on that line.

> R7 says every imported contact gets an email address, but R4 says only contacts from a list with an email column do. Should R7 match R4?

When the wrong part is how the product is built, ask them to describe the problem in user terms and leave how it works to the design doc. Don't restate the code.

## What never goes to the PM

An open security gap, such as a route that lets the wrong users delete records. A PRD is read widely. Put the gap in the design doc and tell the engineer, and word any question around it so it doesn't describe the gap.

A question they could not answer without asking an engineer. Record IDs, edit tracking, which copy of the data we read from. Those go to the design doc. The test is whether they could answer it on their own.
