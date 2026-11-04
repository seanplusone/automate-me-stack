# Project file

Optional. Copy to `<input dir>/project.md` and fill in what the project has. write-edd reads it and never runs anything it names. A field left out means write-edd uses its own default.

```
design_doc_skill: <path to the project's design-doc SKILL.md, plus the checklist, voice and template files it points to>
layout file: <path to the project's layout JSON, copied to <input dir>/layout.json>
design review command: <the command a person runs on the draft, such as a review skill>
EDD file name pattern: <for example docs/design/<date>-<feature>.md>
branch pattern: <for example docs/<feature>-edd>
PR conventions: <title format, labels, reviewers, base branch, anything the PR must link>
```

How write-edd uses each field:
- `design_doc_skill`. edd-draft loads that SKILL.md and the files it points to, and drafts by following them. It feeds in the CS, BR, ARCH, DELTA and ENABLE ids, the PM answers, the corrections and the spikes. The checks still gate the result through the layout. Unset, edd-draft uses its own drafting steps.
- `layout file`. The layout the checks use. It names the sections, the tables, and which section holds each role (hazards, decisions, prd_record). See the README.
- `design review command`. After the panel, the report names this command. The person runs it.
- `EDD file name pattern`, `branch pattern`, `PR conventions`. The EDD is written to that name in the run dir. The report's Hand-off line gives the exact path, branch and PR line. write-edd does not create the branch or the PR.
