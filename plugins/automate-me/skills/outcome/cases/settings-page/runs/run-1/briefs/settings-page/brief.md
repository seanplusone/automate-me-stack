# Brief: Tidy up the cramped account settings page

- Workstream: settings-page
- Kind: ui
- Design facts: ../../../../design-facts.md
- Plan first: none needed. One settings page layout pass.
- Goal: Adjust spacing and section grouping on the account settings page so profile fields and notification toggles have clear separation, following the palette and visual bar in design-facts.md.
- Decision: Whether the updated account settings page layout is ready to ship.
- Context:
  - The account settings page feels cramped; sections run into each other and notification toggles sit tight against profile fields.
  - Design facts file: `../../../../design-facts.md` (palette, locked decisions, and visual bar).
  - Locked decision: keep the left sidebar fixed at 220px.
  - unknown: Which CSS file holds the settings form styles?
- Must-haves:
  - [m1] Separate profile fields and notification toggles into distinct groups with at least 24px between groups and 16px between rows, matching design-facts.md.
  - [m2] Keep the left sidebar width fixed at 220px.
  - out of scope: the billing history table on the other tab.
- Taste: Clear visual grouping between sections, checked in a desktop screenshot against design-facts.md. Flag, don't filter.
- Output: Updated stylesheet and template diff plus before and after desktop screenshots of the account settings page.
- Verify:
  - m1: `test -f ../../../../design-facts.md && grep -q '24px' ../../../../design-facts.md` checks that the spacing bar in design-facts.md is referenced by the layout check.
  - m2: `grep -q '220px' ../../../../design-facts.md` checks that the locked 220px sidebar width is preserved.
- If stuck: Report only. Stop after 2 failed layout passes and never loosen a must-have without asking.
- Skills: none.
- Parking lot:
  - Redesigning the billing history table on the other tab next month.
- Unknowns:
  - unknown: Does this pass need mobile viewports or only desktop?
  - unknown: Which CSS file holds the settings form styles?

## Questions

1. Does this pass need mobile viewports or only desktop?
2. Which CSS file holds the settings form styles?
