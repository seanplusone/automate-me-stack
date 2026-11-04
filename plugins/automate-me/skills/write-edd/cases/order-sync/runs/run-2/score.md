# Score: run-2

All inputs are invented. A blind judge on a separate model scored this run against key.md. The person who wrote the key did not score it.

## Judge totals

29 of 33 found, 4 partial, 0 contradictions of a PM answer.

- Blast radius K1 to K10: 10 of 10. K6 partial on detail (null user not said).
- Hazards H1 to H6: 4 found. H3 and H6 partial.
- Pending decisions: 4 of 4, owner Product.
- PM answers followed: 4 of 4.
- Current state C1 to C4: 4 of 4, plus the expected PM question about the pull overwriting app edits.
- Design P1 to P4: P3 and P4 found. P1 and P2 partial: the design reuses the existing outbox job and cites the jobs standard, but does not state that the job sets the tenant first.

## What the new steps did

- The second-model check caught a misread in current state (CS9, the photo hook) before the design used it. Blast radius described the same hook correctly this time.
- The same check found a cross-customer bug in the precedent job (CS16). The design then added E1 to fix it instead of copying it.
- The CSV importer stayed NOTICED and a hazard. No change to it was designed.
- The delta gate passed with 11 DELTA, 4 ENABLE and 5 NOTICED lines.

## Panel check

Four lenses: premise, correctness, scope, standards. A skeptic kept 11 line items at 80 or more and dropped 18. The run stops at step 8, as designed. Top line items:

1. The job's failed() writes one customer's error text onto every customer's rows, and D9 would show it to users (2 lenses).
2. Retries can send an older change after a newer one for the same order (3 lenses).
3. Under the design's own defaults, the first send queues nothing (2 lenses).
4. Non-admin edits are erased by the next pull, which contradicts the GAP 9 answer (2 lenses).

## Lesson

The judge found no contradiction of a PM answer. The panel found one (finding 4). A single reviewer missed what several lenses caught, which is the reason the panel exists.
