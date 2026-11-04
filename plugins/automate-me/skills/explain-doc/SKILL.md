---
name: explain-doc
description: Turn a long design doc, PRD, runbook or large PR into one page a reader can follow without opening the source. The page gives the big picture through one small example and the main flow as numbered stages with tables. It sums up each section in two sentences and lists what looked wrong while reading. Use for "explain this doc", "break down this EDD", "help me understand this design", or before reviewing someone else's doc or a large PR. Reviewing it is review-pr or a design review; this skill only explains.
---

# Explain a doc

A long doc gets read once, top to bottom, and forgotten. This skill turns it into a page the reader can hold in their head: what problem, what changes, in what order, and what to doubt. It explains. It does not judge the design, post anything or edit the source.

## Run

1. **Read the whole source.** A path, a PR or a link. For a PR, read its description and its whole diff, and see `references/pr.md`. Record two versions in `source.version`: the commit you read at (HEAD of the branch) and the source's own last change. Check the source's status line and dates against `git log` and the code it names. When they disagree (it says draft, the code shipped), say what is true today in `status`, explain the source as written, and list the drift under "looked wrong". Otherwise read code only to understand a sentence or to check a "looked wrong" item.
2. **Pick the words.** Use the system's own terms (record, sync, queue, job, admin, user). A domain word appears only as a bracketed example, as in "a record (e.g. an invoice)", unless the domain is the feature itself (a rain forecast for a weather alert); then keep the word and define it in the legend. Every term you keep goes in the legend, and the page shows its definition on hover. Code names, ticket ids and file paths stay out of the prose, table cells and section names included. They may appear in a legend definition. A repo or product name and a requirement id (P0) may stay in the prose when the legend defines it. Write each legend term in its base form: the hover also matches plurals, "-ed" and "-ing" forms and a capital at the start of a sentence. Pick terms that mean one thing on the page; a common word such as "rule" or "send" catches every use, so name it more fully ("send record").
3. **Find the one example.** The core problem shown on the smallest case that still breaks: three records, two users, one job. Name the items (A, B, C) and set them up once in `example`. The page shows `example` first, then `big_picture`, which uses A, B and C.
4. **Write the map file** as `map.json` in a scratch folder, in the shape in `references/map-shape.md`. The rules that matter:
   - The big picture is at most five sentences. It opens with the problem through the example, then says what the source changes.
   - `decisions` lists what a reader has to decide: open questions, options the source only proposes, and changes that reach every user. Each gets the question, why it matters, and the lines where the source asks it. A decision the code already settled goes under "looked wrong" instead. The page shows them right after the big picture.
   - The main flow is at most five numbered stages, each one to three sentences. When the source has no single process, follow one request or one record through the design. A branch becomes a small table whose first column is the condition (if this is true). Add a "Who acts" column only when a person has to do something. Never a drawn flowchart: auto-layout flowcharts cross lines and the reader gives up.
   - States, if the source has any, are a one-line strip plus a table of every move between states, the way back included. A source with two sets of states gets two entries in `states`.
   - The source's sections, in its order, at most 15. Each gets a name, its line range, one or two plain sentences and at most four points. A section longer than a third of the source splits into its subsections. Any other section with subsections stays one entry, and its points name the subsections that matter. Shorten a heading to plain words when it carries code names or symbols. Untitled lines at the top become a section called "Header".
   - The page's prose stays under 2,500 words. Cut points before you cut sections.
   - Any list a reader would scan (data changes, build order, status, open checks) is a table under `tables`.
   - "Looked wrong while reading" lists at most ten contradictions, gaps and stale lines, the ones that would change a decision, each with its line numbers and a label. Contradictions inside the source come first, then drift from the code. A code name may appear here in backticks when the reader needs it to find the spot. **measured** means you read both lines, or checked the claim in code or data, and the item names which. **inferred** means you reasoned to it. **guess** means you did neither.
5. **Check it.** `$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads. Run `python3 "$SKILL_DIR"/check/check_map.py <map.json>`. It checks the shape, the limits, that every legend term is used, and the writing rules on all prose and legend text. Rewrite only what it flags.
6. **Cold read.** Run `python3 "$SKILL_DIR"/check/render_page.py --text <map.json> > page.txt`. Give a fresh worker on a smaller model (haiku or sonnet) only that file's path and tell it to read nothing else. It answers three questions: what problem does this solve, what changes, and what is the biggest risk. An answer fails when it contradicts the source or leaves out something the source treats as a hard limit (a deadline, a safety rule). Rewrite the part of the map behind each failed answer, then rerun steps 5 and 6 once. If the second run still fails, say so in the reply.
7. **Render and publish.** `python3 "$SKILL_DIR"/check/render_page.py <map.json> > page.html`, then publish `page.html` as an artifact. Publish the map beside it through the artifact's `files` as `map.json`. A later session can then read the map back and edit it. Never hand-write the page. To change how pages look, change `render_page.py`.
8. **Reply** with the link, the example you chose, and the "looked wrong" items, one line each. Say the map is published beside the page as `map.json`.

## Enforced by

- `check_map.py`: the shape, the limits, the legend and the writing check (step 5).
- A second model: the cold read (step 6).
- A person: the reader decides what to do with the "looked wrong" list.
