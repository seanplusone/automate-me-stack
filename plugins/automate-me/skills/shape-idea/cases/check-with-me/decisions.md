# Decisions: plant watering list

## Decided

- goal: a small tool that tells me which house plants need water today
- done: each morning I see the list of plants to water
- output: a chat message with the list that asks "Did you water them?"
- verify: I add two plants with different schedules and check the list on the right days
- constraints: no accounts, it runs on my own laptop
- a plant with an unknown schedule is listed every day
- tools: a plain text file of plants, maybe one line each

## Open

- should a skipped day carry over to the next day?

## Parked

- photos of each plant, later

## Handoff

- next: /automate-me:outcome
- stop: done
- turns: 3
- writing: pass
- map: goal goes to Goal. done goes to Done. output goes to Output. constraints goes to Constraints. verify goes to Verification. Tools, Agents and roles, and Evals stay unknown.
