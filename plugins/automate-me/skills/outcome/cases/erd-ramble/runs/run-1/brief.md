# Brief: Pawpath ERD

- Kind: build
- Plan first: no. The entities are named; the two open questions go to the read-back.
- Goal: Draw an ERD for Pawpath, the dog walking booking app, in Postgres terms.
- Decision: The speaker shows it to the team on Thursday. unknown: What should the team decide from it, the schema itself or only the scope?
- Context: No repo or schema was named. The database is Postgres. Owners pay per booking and the app takes 15 percent.
- Must-haves:
  - Entities walker, owner, dog, booking and payment, each with a primary key. Proof is the diagram.
  - A booking links one walker, one dog and one time slot, as stated. Group walks stay open until answered.
  - A payment belongs to one booking and records the 15 percent fee. Proof is a field on the payment entity.
- Taste: The speaker wants it to "look clean" for Thursday. unknown: What would make it look clean to you, fewer fields shown or only keys and links?
- Output: One mermaid erDiagram with every entity, its fields and types, and each link with its cardinality. Then a list of open points.
- Verify: Every entity and link names the sentence of the ramble behind it, or says guess.
- If stuck: If a link depends on an open question, draw the stated case and list the question. Never model an open point as decided.
- Skills: write-edd later, if the ERD becomes part of a design doc. None runs now.
- Parking lot:
  - Reviews, owners rating walkers. Said "later", so not in the diagram.
  - The landing page copy. Not part of this task.
- Unknowns:
  - unknown: Can a dog have two owners, for example a couple who both use the app?
  - unknown: Can a walker take up to 3 dogs at once on one booking, or is it always one dog?
  - unknown: What should the team decide from it, the schema itself or only the scope?
  - unknown: What would make it look clean to you, fewer fields shown or only keys and links?

## Questions

1. Can a dog have two owners, for example a couple who both use the app?
2. Can a walker take up to 3 dogs at once on one booking, or is it always one dog?
3. What should the team decide on Thursday, and what would make the diagram look clean to you?
