# Decisions: lunch poll

## Decided

- goal: A bot our team can use to pick a lunch spot. People vote, and the winner is where we go.
- done: A person can start a poll, three choices go out, and the winner is posted back in the same chat.
- output: The winner's name only, posted back in the same chat.
- verify: I start a poll with three choices, a second person votes, and I see the winner come back.
- constraints: About 12 people. No payments, nobody orders through the bot.

## Open

- Should the poll close after 20 minutes or when half the team has voted?
- Do we need a tie break?

## Parked

- I think maybe dietary tags later, not sure.
- The office snack drawer is empty again. Someone should buy pretzels.

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 3
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints, done, and every other Decided line go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
