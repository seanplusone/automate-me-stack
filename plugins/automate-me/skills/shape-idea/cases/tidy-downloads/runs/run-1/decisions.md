# Decisions: tidy downloads

## Decided

- goal: I want a small command line tool that tidies my downloads folder. It should move pictures, installers and docs into folders.
- done: pictures, installers, and docs each sit in their own folder
- output: a list of the moves
- verify: I run it on one picture and one installer and check the folders
- constraints: never delete a file

## Open

- Should it run when I ask it or watch the folder all the time?
- is the cutoff 30 days or do I pass the number each time?
- I have no idea what to do with zip files?
- should it touch the desktop too or only Downloads?

## Parked

- my partner uses the same laptop sometimes. What should the tool do about that?
- what do I type to undo a move?
- the desktop icons are a mess, someone should fix that, but that's a different thing

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 5
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints, done, and every other Decided line go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
