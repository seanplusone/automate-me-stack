# Key: erd-ramble

A synthetic case. The app Pawpath and every number are invented. Never show this file to the skill.

Five entities are stated firmly. Two points are thinking aloud: group walks of up to 3 dogs, and a dog with two owners. Both must be asked, not modeled as decided. Reviews are "later", so they stay out of the diagram and go to the Parking lot with the landing page copy. "Clean" is an adjective with no signal.

## Facts, in the speaker's words

Fact: Pawpath
Fact: 15 percent/15%
Fact: 3 dogs
Fact: Postgres
Fact: Thursday

## Slots

Slot: Kind | build
Slot: Goal | ERD
Slot: Must-haves | walker | owner | dog | booking | payment
Slot: Output | diagram/mermaid | field
Slot: Verify | guess
Slot: Context | Postgres

## Gaps that must be asked, not guessed

Unknown: two owners | owner | two/more than one/many
Unknown: group walks | 3 dogs/one dog/several dogs
Unknown: clean | clean/readable/look

## Guesses that fail the run

Forbidden: dog owner join table | \b(dog_owners?|owner_dogs?|dogs_owners)\b
Forbidden: reviews modeled | \breviews?\s*\{|\breviews? table\b|\breview_id\b
Forbidden: group size decided | \bmax(imum)?[_ ]dogs\b|\bup to 3 dogs per (walk|booking)\b

## Parking lot

Parking: reviews | review
Parking: landing page | landing page
