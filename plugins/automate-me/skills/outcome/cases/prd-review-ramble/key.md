# Key: prd-review-ramble

A synthetic case. Dana, the PRD and the product are invented. Never show this file to the skill.

The speaker names the PRD path with "I think", so the path must be confirmed, not taken as fact. The questions the speaker raised (billing, renewal date, pausing twice, annual plans, a support tool) are for the agent to look up in the PRD. They belong in Must-haves, not in the questions to the user. "Good, not twenty nitpicks" is an adjective that needs a number. The pricing page is a tangent.

## Facts, in the speaker's words

Fact: Dana
Fact: Pause subscription
Fact: docs/prd/pause-subscription.md
Fact: 3 months
Fact: Monday

## Slots

Slot: Kind | review
Slot: Goal | gap | question | PM
Slot: Skills | review-prd
Slot: Must-haves | billing | renewal | twice | annual | support
Slot: Verify | section/line | guess
Slot: If stuck | report only/draft only

## Gaps that must be asked, not guessed

Unknown: path | path/docs/prd/pause-subscription.md
Unknown: how many | how many/at most/cap
Unknown: decision | review/Monday

## Guesses that fail the run

Forbidden: answers billing | \b(billing|charges?) (stops|pauses|is paused|continues)\b
Forbidden: question count invented | \b(at most|no more than|max(imum)? of|up to) (5|8|10|12|15)\b
Forbidden: posts to the PRD | \b(post|add|comment) (the questions )?(on|to|in) the PRD\b

## Parking lot

Parking: pricing page | pricing page | toggle
