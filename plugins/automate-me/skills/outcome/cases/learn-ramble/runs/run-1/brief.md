# Brief: Learn how database indexes work

- Kind: learn
- Plan first: no. One topic, one session.
- Goal: Explain how an index speeds up a query, and when it does not, using the slow orders query as the example.
- Decision: Whether to add the index someone suggested for the orders query, and how to explain why in standup.
- Context:
  - The orders page is slow. The query takes "like 4 seconds".
  - It filters orders by customer_id and sorts by created_at. The database is Postgres.
  - The speaker "kind of" knows what a b-tree is, so start there and check it.
- Must-haves:
  - Cover a two-column index on customer_id then created_at, and why the column order matters.
  - Cover at least one case where an index does not help. Proof is a query plan.
- Taste: A small example the speaker can run. Flag, don't filter.
- Output:
  - A short explanation in plain words, built on one runnable example.
  - Then a check of understanding: 3 questions the speaker answers, with the answers folded below.
- Verify: Every claim about how Postgres behaves cites a source (the Postgres docs section) or a query plan from the example, or says guess.
- If stuck: Report only. Run the example in a throwaway local database; never create an index on a shared database. Stop and ask if the example cannot run.
- Skills: explain-doc if a long doc on indexes needs a one-page read. None runs yet.
- Parking lot:
  - Moving to a different database entirely. A separate question.
- Unknowns:
  - unknown: Which Postgres version is it?
  - unknown: About how many rows does the orders table hold?
  - unknown: Where may the example run, a throwaway local database or a copy of the real one?

## Questions

1. Which Postgres version is it, and about how many rows does the orders table hold?
2. Where may the example run, a throwaway local database or a copy of the real one?
