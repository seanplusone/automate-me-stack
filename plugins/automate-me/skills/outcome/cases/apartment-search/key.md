# Key: apartment-search

A synthetic case, built from a spoken example. The listings and people are invented. Never show this file to the skill.

The speaker gives the rent split (2600 and 1700), a stretch budget of 5k, and a count of 10. The sum of the split is 4300. Whether 4300 is a hard cap, or 5k is, was never said, so the brief must ask. "Modern" and the carpet rule are taste, checked in photos. The Facebook group is a tangent.

## Facts, in the speaker's words

Fact: 3 bed
Fact: 2 bath
Fact: Irvine
Fact: 2600
Fact: 1700
Fact: 5k/5000
Fact: 10
Fact: 100 dollars/$100

## Slots

Slot: Kind | search
Slot: Taste | modern | carpet | bedroom | flag | photo
Slot: Verify | photo/picture | description | senior/second reviewer/reviewer
Slot: Output | 10
Slot: Plan first | parallel
Slot: Must-haves | 3 bed | 2 bath | Irvine
Slot: If stuck | next 100/$100
Slot: Skills | browser | save what worked

## Gaps that must be asked, not guessed

Unknown: decision | tour/apply
Unknown: move-in | move-in/move in
Unknown: cap | 4300 | 5k/5000
Unknown: area | commute/neighborhood/area
Unknown: pets | pet

## Guesses that fail the run

Forbidden: move-in date | move[- ]in[^.\n]{0,30}\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|move[- ]in[^.\n]{0,30}\b\d{1,2}/\d{1,2}\b
Forbidden: neighborhood | \b(woodbridge|turtle rock|northwood|university park|westpark|quail hill|portola springs|great park|spectrum|el camino real)\b
Forbidden: pet policy | \b(no pets|pets? (allowed|ok|friendly)|cat|dog)\b
Forbidden: 4300 as the cap | \b(cap|max|maximum|limit|budget)\b[^.?\n]{0,25}\b4300\b

## Parking lot

Parking: facebook | facebook

## Learn step

The brief names the learn step in its Skills slot (`save what worked`). Whether the run really offers it once, after something great turns up, is checked by a person.
