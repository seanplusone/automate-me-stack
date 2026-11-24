---
name: check-palette
description: Fail a web page whose large backgrounds are beige, cream or off-white, the warm default AI tools pick, unless the user allows beige. With a palette file, also fail any background far from the locked colors. Use after building or restyling a page, and before saying its colors are done.
---

# check-palette

Load the real page in headless Chromium at 1280x800, read the computed background color of each large element, and fail on beige.

`$SKILL_DIR` is this skill's directory.

## When to run it

Run it after you build or restyle a page, and before you say the colors are done. Run it again after each color fix.

```bash
python3 "$SKILL_DIR"/check/check_palette.py <url or page.html>
python3 "$SKILL_DIR"/check/check_palette.py <url> --palette palette.json   # also hold it to a locked palette
```

- `--allow-beige`, or `--brief FILE` with a line `allow beige: yes`, allows beige. Allow it only when the user asked for it.
- `--palette` takes a JSON list of `#RRGGBB` colors, or an object of name to color. Each background must be within `--max-delta` (default 5, CIEDE2000) of one of them. White and gray count too, so list them if the page uses them. A beige palette color does not allow beige.
- `--min-area` (default 10000 px2) sets the smallest box checked. The page canvas is always checked: the `html` background, else the `body` background, else white. When `html` has its own background, `body` is checked like any other element.

## Reading the output

Each failure is one line, `FAIL <selector> <#hex> <reason>`. The reason is `beige (H=.. S=..% L=..%)` or `off-palette (nearest <#hex>, deltaE=..)`. The last line is `CHECK-PALETTE: OK` or `CHECK-PALETTE: FAIL (n)`. Exit 0 is OK and exit 1 is FAIL. Exit 2 means the check could not run, and it is never a pass. A missing page, a bad or empty palette file, a `--max-delta` or `--min-area` that is negative or not finite, and a missing Playwright all exit 2. Fix the setup and run it again.

Each background is judged as it renders: mixed over its ancestors' backgrounds and scaled by the opacity of its box and its ancestors. Boxes at `opacity: 0` are skipped. An ancestor with `display: contents` or that is not visible paints no background.

## The beige bounds

Beige is a hue of 25 to 60 degrees, a saturation of at least 10% and a lightness of 88% to 98%. That range holds the washed-out warm off-whites: cream, parchment, linen and "paper". Below 10% saturation the color reads as gray. Below 88% lightness it is a chosen tan or color. Above 98% it is white. So `#FAF9F5`, `#F0EEE6` and `#FFFDD0` fail, and `#FFFFFF`, `#F5F5F5` and `#FFE0B2` pass.

## What it does not check

Text color, borders, images, gradients and their stops, `contain: paint`, `mix-blend-mode`, `filter`, `backdrop-filter`, hover and focus states, and anything drawn after a click. It checks one viewport width only. It also flags a beige background that another element fully covers, and it can misjudge a translucent group nested inside another one. Look at those yourself, or say they were not checked.

## Tests

`check/test_check_palette.py` runs the script on each page in `cases/`. Then it breaks one rule at a time in a copy of the script and fails if any broken copy still passes.
