# Brief: ERD for Pawpath

- Kind: build
- Plan first: none needed
- Goal:
  - draw an ERD for Pawpath, the dog walking booking app
  - the ERD will be shown to the team on Thursday
- Done:
  - entities: walkers, owners, dogs, bookings, payments (proof: each appears in the diagram)
  - a booking is one walker, one dog, one time slot (hedged, confirm)
  - the owner pays per booking, and we take 15 percent (proof: payments link to bookings, with the 15 percent in a column or note)
  - Postgres (proof: column types are valid Postgres types)
- Taste (flag, don't filter): should look clean; shown by no crossing lines and readable labels
- Output: an ERD diagram of the five entities, shown to the team; format unknown
- Constraints:
  - out of scope: reviews, owners rating walkers
  - report only; never loosen a done line without asking
- Tools:
  - The database is Postgres. A diagram tool that can render the drawing. Check it works first.
  - write first: none. Nothing else existing is named.
- Agents and roles:
  - how: single pass
  - One agent draws the diagram.
- Run mode: one-at-a-time
- Evals:
  - Pass: the five entities appear, and an open point stays open.
  - Fail: an open point is drawn as already decided.
- Verification: every claim names the entity, rule or line behind it, or says guess; a check that renders the diagram needs a diagram tool
- Skills:
  - none run yet
- Parking lot: reviews later; the landing page copy is terrible and someone should fix it
- Unknowns:
  - unknown: can a walker take up to 3 dogs at once?
  - unknown: can a dog have two owners?
  - unknown: how large will the app get (users, bookings)?
  - unknown: who owns each part, and what schema already exists?
  - unknown: what format should the diagram be in?

## Questions

1. Can a walker take up to 3 dogs at once, and can a dog have two owners?
2. What format should the ERD be in for Thursday?
3. Does any schema already exist, and how large should it scale?
