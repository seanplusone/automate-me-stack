# Key: settings-page

A synthetic case. The settings page and layout are invented. Never show this file to the skill.

This is a ui brief. It must point to the Design facts file, keep the locked 220px sidebar width, and leave the billing history table in the Parking lot. The speaker never says whether mobile viewports are in scope or which CSS file holds the form styles. The brief must ask, not guess.

## Facts, in the speaker's words

Fact: 220px
Fact: design-facts.md
Fact: account settings
Fact: notification toggles
Fact: profile fields

## Slots

Slot: Kind | ui
Slot: Design facts | design-facts.md
Slot: Goal | account settings | spacing
Slot: Must-haves | 220px | notification toggles
Slot: Output | screenshot/diff
Slot: If stuck | report only

## Gaps that must be asked, not guessed

Unknown: viewports | mobile | desktop
Unknown: stylesheet | css/stylesheet

## Guesses that fail the run

Forbidden: css path invented | \b(src|styles)/[\w./-]+\.css\b
Forbidden: breakpoint invented | \b(320|375|480|640|768)px\b

## Parking lot

Parking: billing table | billing history
