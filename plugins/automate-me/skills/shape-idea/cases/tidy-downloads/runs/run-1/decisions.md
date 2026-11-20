# Decisions: tidy Downloads

## Decided

- goal: a small command line tool that tidies my Downloads folder and moves pictures, installers, and docs into folders
- done: pictures, installers, and docs each sit in their own folder
- output: a list of the moves
- verify: I run it on one picture and one installer and check the folders
- constraints: never delete a file, and leave anything newer than 30 days where it is

## Open

- should it run when I ask, or watch the folder all the time?
- should it touch the desktop too, or only Downloads?
- what do I do with a zip file?
- what do I type to undo a move?

## Parked

- is the cutoff 30 days or do I pass the number each time?
- the desktop icons are a mess, someone should fix that, but that is a different thing

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 5
- writing: pass
- map: goal goes to Goal. output goes to Output. verify goes to Verify. constraints, done, and every other Decided line go to Must-haves. Open goes to Unknowns. Parked goes to the Parking lot.
