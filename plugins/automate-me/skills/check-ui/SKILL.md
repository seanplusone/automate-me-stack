---
name: check-ui
description: "Measure a rendered page for excess white space, uneven gaps, mismatched padding, a broken left edge, and sideways scroll. Use after a UI change, or when a layout looks sparse or misaligned. Works for any stack and any coding agent."
---

# check-ui

verify-web proves what a page does. This skill measures how the page is laid out. A card taller than its content, a gap that ignores grouping, padding that drifts, a broken left edge, or a phone page that scrolls sideways fails here.

The command is the whole check. Claude Code, Codex, and Grok Build run the same command. This file only says when to run it and how to read the report.

`$SKILL_DIR` is the folder that holds this file. Claude Code prints it as "Base directory for this skill" when the skill loads. In Codex and Grok Build it is the folder of this SKILL.md.

## When to use it

Run it after a UI change, once the page renders. Run it when a built page looks sparse, uneven, or misaligned. Run it before calling a layout done.

Do not use it to prove a click, a save, or a permission. That is [verify-web](../verify-web/SKILL.md).

## Install

From this folder, once per machine:

```
npm install
npx playwright install chromium
```

The only dependency is Playwright, which downloads Chromium. If Chromium will not start because a system library is missing, install the library it names and run the second command again.

## Run

Always measure both widths. 390 is a phone. 1280 is a desktop.

```
node "$SKILL_DIR"/check/measure.mjs --url page.html --widths 390,1280
node "$SKILL_DIR"/check/measure.mjs --url https://127.0.0.1:3000/settings --widths 390,1280 --config rules.json --out report.json
```

`--url` is an http or https URL, or a path to an HTML file. `--widths` defaults to 390 and 1280. `--config` is optional. `--out` writes the same JSON the command prints.

Exit 0 when every rule passes. Exit 1 when a rule fails. The report is still printed. Exit 2 when the arguments are wrong, the browser is missing, or the page does not load. A page that does not load is never a pass. `--help` prints usage and exits 0.

## Rules

Both widths, on every run.

| Id | What it measures |
|---|---|
| G1 | A card is no taller than its content plus its own padding and border. Tolerance is 4px. At 1280 the main column is at least 60 percent of the viewport. |
| G2 | The gap between groups is at least 2 times the gap inside a group. Design notes often use 3 or 4 times. Raise the ratio for that. |
| G3 | Containers of one kind share padding within 2px. Kind is the role plus the class list. |
| G4 | Headings, paragraphs, cards, and buttons in a column share a left edge within 2px. A horizontal row counts as one edge, the leftmost item. |
| G9 | The document scroll width is not wider than the viewport. This includes the 390px width. |

A card is an element with `data-ui` of `card`, `tile`, or `panel`, or a class token `card`, `tile`, `panel`, or one ending in `-card`, `-tile`, or `-panel`. A group uses `data-ui="group"` or a class token `group` or ending in `-group`. The column is `data-ui="column"` or `data-ui="main"`. With neither, the column is the `main` element.

Text and controls inside a card are not part of the column's left edge. Fixed and absolute boxes are left out of the gap check and the left-edge check.

## Report

The command prints one JSON object. The shape is [check/report.schema.json](check/report.schema.json).

```json
{
  "page": "page.html",
  "widths": [
    {
      "width": 390,
      "rules": [
        {
          "id": "G1",
          "status": "pass",
          "element": "#plan",
          "measured": { "height": 90, "slackBottom": 0 },
          "limit": { "whitespacePx": 4 },
          "message": "Card height matches its content plus padding."
        }
      ]
    }
  ],
  "verdict": "pass"
}
```

`status` is `pass`, `fail`, or `skip`. `verdict` is `fail` when any row is `fail`. A skip means the page had nothing for that rule to measure. Skips do not fail the verdict. Read the rows before treating an all-skip report as a clean page.

## Config

Copy [rules.example.json](rules.example.json) into the project and pass it with `--config`. An unknown key fails the run.

| Key | Default | Meaning |
|---|---|---|
| whitespacePx | 4 | Extra space allowed inside a card, past content and padding. |
| paddingPx | 2 | How far padding may drift inside one kind. |
| alignPx | 2 | How far a left edge may drift from the shared line. |
| scrollPx | 0 | Extra pixels allowed past the viewport before G9 fails. |
| betweenOverInside | 2 | Minimum ratio of the between-group gap to the inside gap. |
| minWidthRatio | 0.6 | Minimum main-column width, as a fraction of the viewport, at columnAtWidth. |
| columnAtWidth | 1280 | Viewport width at which the column ratio runs. |
| auto | true | Class-name guesses. data-ui and selectors still apply when this is false. |
| selectors | see the example | CSS selectors for cards, groups, columns, headings, body, buttons, and containers. They add matches. |

Mark an element in the page when the guess is wrong.

| Attribute | Counts as |
|---|---|
| data-ui="card" | A card. `tile` and `panel` count too. |
| data-ui="group" | A group. |
| data-ui="column" | The main column. `main` counts too. |
| data-ui="container" | A container for the padding rule. |
| data-ui="heading" | A heading. |
| data-ui="body" | Body text. |
| data-ui="button" | A button. |

## Limits

These five rules do not pass a page. They catch a few layout defects. A later check will diff regions of the page against a mockup. Contrast, type, token lint, craft rules, and per-project preferences are not in this version.

The column check uses `main`, unless a selector or `data-ui="column"` names a tighter box. A full-bleed main with a narrow inner wrapper can pass until that wrapper is marked.

A card with only text and no child element is measured from that text. A card taller than that text still fails G1.

## Checks

```
node "$SKILL_DIR"/check/test_geometry.mjs
python3 "$SKILL_DIR"/check/test_cases.py
```

`test_geometry.mjs` feeds plain boxes to the rules. It does not open a browser. `test_cases.py` runs measure on `cases/`. One page passes every rule at both widths. Each other page fails the rule named in its `key.json` and no other rule. The report is checked against the schema. A page that does not load exits 2.

If Playwright or Chromium is missing, `test_cases.py` prints SKIP and exits 0. That is not a pass of the pages. Install with the commands above and run it again.

The practice pages are generic HTML. They are not copied from a product.
