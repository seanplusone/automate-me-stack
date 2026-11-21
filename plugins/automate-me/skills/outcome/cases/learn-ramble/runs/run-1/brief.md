# Brief: Learn how database indexes work

- Kind: learn
- Plan first: none needed. One topic, one session.
- Goal:
  - Explain how an index speeds up a query, and when it does not, using the slow orders query as the example.
  - The orders page is slow. The query takes "like 4 seconds". It filters orders by customer_id and sorts by created_at.
  - The speaker "kind of" knows what a b-tree is, so start there and check it.
  - Whether to add the index someone suggested, and how to explain why in standup.
- Done:
  - Cover a two-column index on customer_id then created_at, and why the column order matters.
  - Cover at least one case where an index does not help. Proof is a query plan.
- Taste: A small example the speaker can run. Flag, don't filter.
- Output:
  - A short explanation in plain words, built on one runnable example, which the speaker reads.
  - Then a check of understanding: 3 questions the speaker answers, with the answers folded below.
- Constraints: Report only. Run the example in a throwaway local database; never create an index on a shared database. Stop and ask if the example cannot run.
- Tools:
  - The database is Postgres. Use the Postgres docs and a throwaway local database. Check the database starts.
  - write first: the example query, before the explanation.
- Agents and roles: One agent explains. The speaker answers the check. No split.
- Evals:
  - Pass: the explanation uses the orders query and cites a source.
  - Fail: it names a Postgres version the speaker did not give.
- Verification: Every claim about how Postgres behaves cites a source (the Postgres docs section) or a query plan from the example, or says guess.
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
