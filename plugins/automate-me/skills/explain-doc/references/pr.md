# Explaining a PR

Read the PR's description, every changed file and its review comments with `gh`, read only. Never comment, review or approve. Record the head commit in `source.version` and the PR link in `source.link`.

## A PR that adds or changes a doc

The doc is the source. Explain the doc at the PR's head commit, and use its line numbers. Mention any other file in the PR (an index row, a template) in one point of the "Header" section.

## A PR that changes code

The source is the change, not each file.
- The flow is what one request, job or record goes through after the change, with the changed steps named in plain words.
- Sections are groups of files by purpose (the new table, the endpoint, the screen, the tests). Each section has `files` in place of `lines`: the paths, short form.
- "Looked wrong" items cite `files` (a path with a line) in place of `lines`.
- `decisions` holds what the PR leaves open: a TODO, a flag left off, a behavior the description doesn't mention.
