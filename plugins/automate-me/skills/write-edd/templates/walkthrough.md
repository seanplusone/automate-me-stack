# Walkthrough

`out/walkthrough.md` explains write-edd's findings to the person running it. The playbook appends one entry after step 3 (current state), step 4 (blast radius), step 6 (design options) and step 10 (panel). Load `../shared/writing-rules.md` first. Run `check_edd.py writing out/walkthrough.md` after each append.

Each entry is at most one screen.

The walkthrough also teaches how an EDD is built, for a person still learning to write one. The first entry opens with the picture below. Every entry names the EDD section its step feeds, from the table under it.

## The bigger picture

An EDD answers one question for each part of the work. Each step of write-edd answers one of them, and each answer lands in a named section of the EDD.

| Piece | The question it answers | Where it lands |
|---|---|---|
| PRD and PM answers | What must change, and why? | The R, GAP and ANSWER ids every change cites |
| Current state | How does the code do this today? | The "today" each change in Data model, Backend and Frontend is compared against |
| Blast radius | What else reads or writes what we change? | Known hazards, or a line saying it stays unchanged |
| Design options | What shape should the change take, and is there one already? | Architecture, and Decisions blocking build start for a choice still open |
| Spikes and evidence | What did we prove by running something? | The evidence behind a hazard or a decision |
| The EDD | Is the whole plan clear and safe to build? | Every section, read by reviewers |
| Delivery slicing | In what order can it ship? | The PRs, each one small enough to review |

## What each step is for

| Step | Feeds | A good one | A weak one |
|---|---|---|---|
| Current state | Data model, Backend, Frontend | Each step cites its line, read from the code | A guess from method names |
| Blast radius | Known hazards | Each hook, scope, writer and reader, with its line | Only what a grep found |
| Design options | Architecture, Decisions | Reuses or configures what exists, and says where | A new kind of thing beside one that already does the job |
| Panel | Every section | Findings that survived a skeptic | A list of style notes |

```
## <step name>

Feeds: <the EDD section, from the table above>. <One sentence on what that part of an EDD is for.>

<One sentence that removes the misconception a reader most likely has about this part.>

<The shape in two or three sentences, before any detail.>

**<Finding, as a short name>**
- What it means: <for users, or for the build.>
- How sure: <measured, inferred or guess, with its id.>
- Decide: <what the person needs to decide, or leave the line out.>

<details>
<summary>Supporting detail</summary>

<File and line walks, tables, raw output.>

</details>
```

Rules:
- The opening sentence is about the part, not the run. "The pull does not read back what the app sends" is an opening. "This section summarizes current state" is not.
- The shape comes before the detail. A reader who stops after the shape still has the picture.
- One block per finding. Findings that need no decision omit the Decide line.
- Every claim carries its label and id (W18 in the writing rules). A claim with no evidence is marked guess.
- Detail goes in `<details>`. The entry reads without opening it.
- A finding the person must decide on also appears in the report's decisions line. The walkthrough explains it, the report lists it.
