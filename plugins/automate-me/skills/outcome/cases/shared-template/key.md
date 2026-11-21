# Key: shared-template

A synthetic case. The workshop and the cards are invented. Never show this file to the skill.

One shared template makes a batch. It fits name-the-tool cards. It bans a second object, so an order-the-steps card cannot show its sequence. The brief must flag that before any card is made. "A few" order cards is not a count, so the brief must ask. The check is blind, on the half-sheets people actually hold.

## Facts, in the speaker's words

Fact: 24
Fact: name-the-tool
Fact: order-the-steps
Fact: sand
Fact: stain
Fact: seal
Fact: four labels
Fact: half-sheets

## Slots

Slot: Evals | cannot show order-the-steps/breaks on order-the-steps/does not fit order-the-steps
Slot: Verification | cards blind | half-sheet

## Gaps that must be asked, not guessed

Unknown: how many order cards | how many | order-the-steps

## Guesses that fail the run

Forbidden: invented count or a denied check | (?q)\bnot blind\b|\bno ban\b|\bworks for order\b|\bfull-page\b|\b(?:\d+|one|two|three|four|five|six)(?:\s+or\s+(?:\d+|one|two|three|four|five|six))?\s+order-the-steps\b|\b(?:\d+|one|two|three|four|five|six)\s+or\s+(?:\d+|one|two|three|four|five|six)\b
