# Brief: ERD for Pawpath

- Kind: build
- Plan first: none needed
- Goal: draw an ERD for Pawpath, the dog walking booking app
- Decision: the ERD will be shown to the team on Thursday
- Context: Pawpath is a booking app; entities named are walkers, owners, dogs, bookings, payments; Postgres; nothing else existing is named
- Must-haves:
  - entities: walkers, owners, dogs, bookings, payments (proof: each appears in the diagram)
  - a booking is one walker, one dog, one time slot (hedged, confirm)
  - the owner pays per booking, and we take 15 percent (proof: payments link to bookings, with the 15 percent in a column or note)
  - Postgres (proof: column types are valid Postgres types)
  - out of scope: reviews, owners rating walkers
- Taste (flag, don't filter): should look clean; shown by no crossing lines and readable labels
- Output: an ERD diagram of the five entities; format unknown
- Verify: every claim names the entity, rule or line behind it, or says guess; a check that renders the diagram needs a diagram tool
- If stuck: report only; never loosen a must-have without asking
- Skills:
  - none run yet
  - how: single pass
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
