---
name: check-palette
description: Fail a web page whose large backgrounds are beige, cream or warm off-white, unless the user allows beige. AI tools often pick these colors by default. With a palette file, also fail any background far from the locked colors. Use after building or restyling a page, and before saying its colors are done.
---

# check-palette

The script loads the page in headless Chromium at 1280x800. It reads the computed background color of each large element and fails on beige.

`$SKILL_DIR` is this skill's directory.

## When to run it

Run it after you build or restyle a page, and before you say the colors are done. Run it again after each color fix.

```bash
python3 "$SKILL_DIR"/check/check_palette.py <url or page.html>
python3 "$SKILL_DIR"/check/check_palette.py <url> --palette palette.json   # also hold it to a locked palette
```

- `--allow-beige`, or `--brief FILE` with a line `allow beige: yes`, allows beige. Allow it only when the user asked for it.
- `--palette` takes a JSON list of `#RRGGBB` colors, or an object of name to color. Each background must be within `--max-delta` (default 5, CIEDE2000) of one of them. White and gray count too, so list them if the page uses them. A beige palette color does not allow beige.
- `--min-area` (default 10000 square pixels) sets the smallest box checked. The page canvas is always checked. The canvas color is the `html` background, or the `body` background when `html` has none, or white when neither has one. When `html` has its own background, `body` is checked like any other element.

## Reading the output

Each failure is one line, `FAIL <selector> <#hex> <reason>`. The reason is `beige (H=.. S=..% L=..%)` or `off-palette (nearest <#hex>, deltaE=..)`. The last line is `CHECK-PALETTE: OK` or `CHECK-PALETTE: FAIL (n)`. Exit 0 is OK and exit 1 is FAIL. Exit 2 means the check could not run, and it is never a pass. The script exits 2 on a missing page, a bad or empty palette file, a missing Playwright or Chromium, and a `--max-delta` or `--min-area` that is negative or not finite. Fix the setup and run it again.

The script judges each background as it renders, mixed over its ancestors' backgrounds. An ancestor's opacity applies to the element and its descendants as one group, as the browser paints it. The script skips a box at `opacity: 0` and a box that another opaque element covers fully. An ancestor that has `display: contents` or is not visible adds no background to the mix.

## The beige bounds

Beige is a hue of 25 to 60 degrees, a saturation of at least 10% and a lightness of 88% to 98%. That range holds the pale warm off-whites, such as cream, parchment, linen and paper. Below 10% saturation the color looks gray. Below 88% lightness it is a deliberate tan or other color. Above 98% it is white. So `#FAF9F5`, `#F0EEE6` and `#FFFDD0` fail, and `#FFFFFF`, `#F5F5F5` and `#FFE0B2` pass.

## What it does not check

It does not check text color, borders, images, gradients, `contain: paint`, `mix-blend-mode`, `filter` or `backdrop-filter`. It does not check hover or focus states, or anything drawn after a click. It checks only the first 1280x800 viewport, so it skips boxes below it. Look at these yourself, or say they were not checked.

It also gets these cases wrong:

- An overlay with `pointer-events: none` does not count as covering, so the box under it is still checked.
- A box that an `overflow: hidden` ancestor clips away can still be flagged. The script samples 9 points with `elementsFromPoint`, and it treats a point that misses the box as visible.
- An overlay with `background-clip: content-box` counts as covering its whole box, even where it does not paint. So visible beige in its padding area can be missed.
- A translucent overlay is mixed only with its ancestors, not with siblings that overlap it. So it can be judged against the wrong backdrop.

## Tests

`check/test_check_palette.py` runs the script on each page in `cases/`. Then it breaks one rule at a time in a copy of the script, and the test fails if any broken copy still passes.
