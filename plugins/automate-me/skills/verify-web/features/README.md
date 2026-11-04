# Feature recipes

One file per feature: how to reach it, what data it needs, what to drive, and how to prove the
result. Read this index, then the feature's file. A recipe is the maintained source for verifying
that feature; update it whenever a run finds a step it got wrong.

These recipes are examples for the demo app in `../cases/demo-app/`. Keep your own project's recipes
next to its config, in `.claude/verify-web/features/`, and list them in an index like the one below.

## Baseline preconditions

- The doctor prints `DOCTOR: OK`.
- You know which tree serves the page and which tree runs the jobs; the doctor prints both. A change
  you are proving must be in the tree the feature runs.
- You are on an app with `test_data: true`, signed in as the default persona unless the recipe
  names another ([`personas.md`](../personas.md)).

## Driving conventions

- One browser page per run, opened at the start and closed at the end.
- Locate controls from the accessibility snapshot by role, accessible name, label or `name=`
  attribute, then click or fill them. Never by coordinate.
- Advance only through the UI. An API call or SQL write that skips a step voids the run.
- Record every id a run creates so cleanup can find it.

## Proof and skip reporting

- Snapshot and screenshot before and after the action, with the URL visible.
- A change is proven by a second, read-only view: the row in the database, a read-only API call, or
  the record reopened in a fresh page load.
- Console errors and non-2xx requests are findings, even when the screen looks right.
- An entry point you could not reach is reported with the attempted step and the unmet
  precondition. Never report it as verified through a different entry point.

## How to add a recipe

Copy this into `<feature>.md` and fill in every section. Write it after the first run that needed
setup you had to work out, while the steps are fresh.

```markdown
# <Feature name>

Covers: <the screens and actions this recipe drives>
Last driven: <YYYY-MM-DD>, <tree branch and sha>, <result>

## Reach it
- Persona: <persona>
- Path: <menu clicks or URL from the landing page>

## Data
- Needs: <records that must exist first, and how to create them through the app>
- Reset: <how to get back to the starting state through the app>

## Drive
1. <user step>
2. <user step>

## Prove
- On screen: <what the user should see>
- Second way: <the read-only check: query, API call, fresh page>
- Known noise: <console messages or requests that are expected, and why>

## Clean up
- <how to undo what the run created, through the app>
```

## Recipes

| Feature | Covers | Last driven |
|---|---|---|
| [Refund an order](./demo-refund-order.md) | Demo app: orders list, Refund button, the order's refund history, read-only user | one click and double-click, by `check/run_pr_case.js` |
