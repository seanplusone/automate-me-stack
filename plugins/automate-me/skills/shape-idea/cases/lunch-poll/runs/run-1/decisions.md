# Decisions: lunch poll bot

## Decided

- goal: a bot our team can use to pick a lunch spot. people vote, and the winner is where we go
- done: a person can start a poll, three choices go out, and the winner is posted back in the same chat
- constraints: no payments, nobody orders through the bot, for about 12 people
- output: the winner's name only, posted back in the same chat
- verify: I start a poll with three choices, a second person votes, and I see the winner come back

## Open

- should the poll close after 20 minutes or when half the team has voted?
- do we need a tie break?

## Parked

- maybe dietary tags later, not sure
- the office snack drawer is empty again, someone should buy pretzels

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 3
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints, done, and every other Decided line go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
