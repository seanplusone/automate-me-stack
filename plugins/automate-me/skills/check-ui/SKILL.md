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
node "$SKILL_DIR"/check/measure.mjs --url http://127.0.0.1:3000/settings --widths 390,1280 --config rules.json --out report.json
```

`--url` is an http or https URL, or a path to an HTML file. `--widths` defaults to 390 and 1280. `--config` is optional. `--out` writes the same JSON the command prints. `--shots` is the folder for crops of rows that need a look. When it is omitted, crops go in a temporary folder and the report names that path. `--wait-for` is a selector to wait for after load. `--timeout` is the whole run, in milliseconds.

The page loads, then the tool waits until the DOM and any animation have been still for about half a second. That wait stops at 3 seconds. Content that arrives later needs `--wait-for`. A page with almost no text, a skeleton, an empty app shell, a spinner, or an error heading needs a look. That includes a status code and a short message in another language. A form is not a data region, so a centered sign-in form can use `display: grid`.

Exit 0 when every rule passes. Exit 1 when a rule fails. Exit 3 when nothing fails but a row needs a look. Exit 2 when the arguments are wrong, the page does not load, or the run is inconclusive. The report names the reason. A blank page, or the page's own script dying before the first paint, is inconclusive. A console error, a widget error, or a failed iframe is a warning. `--help` prints usage and exits 0.

## Rules

Both widths, on every run.

| Id | What it measures |
|---|---|
| G1 | A card is no taller than its content plus its own padding, border, and the child margins. Tolerance is 16px in total, and the gap must also exceed 3 percent of the card. At 1280 the main column is at least 60 percent of the viewport. |
| G2 | The gap between groups is at least 2 times the gap inside a group. Design notes often use 3 or 4 times. Raise the ratio for that. |
| G3 | Containers of one kind share padding within 2px. Kind is the role plus the class list. |
| G4 | Headings, paragraphs, cards, and buttons in a column share a left edge within 2px. The check uses the spread, not the distance from the middle. A horizontal row counts as one edge, the leftmost item. Right-aligned and centered items are ignored. |
| G9 | The document scroll width is not wider than the viewport. This includes the 390px width. |

A card is an element with `data-ui` of `card`, `tile`, or `panel`, or a class token `card`, `tile`, `panel`, or one ending in `-card`, `-tile`, or `-panel`. A box with a border, a solid background, or a shadow is also a card, even when the padding sits on its child. A group uses `data-ui="group"` or a class ending in `-group`. The bare class `group` is not a group. The column is `data-ui="column"` or `data-ui="main"`, then the `main` element, then the body.

Text inside a card, a padded box, a list, or a quote is not part of the column's left edge. Open shadow roots are measured. Iframes are skipped and named in the report.

A box with overflow hidden is a frame when its content covers most of the height, or when it holds a code block, a canvas, or a video. A gradient laid over a picture is not a card. A box that only wraps a footer is not a card. Content taken out of flow still counts when it covers the card.

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

`status` is `pass`, `fail`, `skip`, or `review`. `review` means the box was a guess and the guess is weak. A selector in the config is never a guess. `verdict` is `fail` when any row fails, and `review` when the only open rows need a look. The `review` list names each of those rows and the crop saved for it. If every row is a skip, the verdict is `inconclusive` and the command exits 2.

## Config

Copy [rules.example.json](rules.example.json) into the project and pass it with `--config`. An unknown key fails the run.

| Key | Default | Meaning |
|---|---|---|
| whitespacePx | 16 | Extra space allowed inside a card, past content and padding. |
| paddingPx | 2 | How far padding may drift inside one kind. |
| alignPx | 2 | How far a left edge may drift from the shared line. |
| scrollPx | 0 | Extra pixels allowed past the viewport before G9 fails. |
| betweenOverInside | 2 | Minimum ratio of the between-group gap to the inside gap. |
| minWidthRatio | 0.6 | Minimum main-column width, as a fraction of the viewport, at columnAtWidth. |
| columnAtWidth | 1280 | Viewport width at which the column ratio runs. A run that omits it records a skip. |
| columnExemptions | prose, signin | A reading column of 55 to 80ch in the paragraph font, or a form with a password field. Code, figures, and asides can sit in the reading column. A table or a grid cannot. Set this to [] to turn both off. |
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

The column check uses `main`, unless a selector or `data-ui="column"` names a tighter box. A full-bleed main with a narrow inner wrapper can pass until that wrapper is marked. A reading column of about 55 to 80ch, and a single centered sign-in card or form, are skips. The skip names the exemption. A dashboard column under 60 percent still fails.

A card with only text is measured from its line box, not the ink. Child margins count as content. A grid or flex row is compared with the tallest text in that row.

## Checks

```
node "$SKILL_DIR"/check/test_geometry.mjs
python3 "$SKILL_DIR"/check/test_cases.py
```

`test_geometry.mjs` feeds plain boxes to the rules. It does not open a browser. `test_cases.py` runs measure on `cases/`. The clean page passes every rule at both widths. Planted pages fail the rule named in `key.json`. Pages that cannot be judged exit 2. The report is checked against the schema. A page that does not load exits 2.

If Playwright or Chromium is missing, `test_cases.py` prints SKIP and exits 0. That is not a pass of the pages. Install with the commands above and run it again.

The practice pages are generic HTML. They are not copied from a product.
