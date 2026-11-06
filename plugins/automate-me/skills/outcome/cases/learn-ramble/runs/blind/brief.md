# Brief: Understand database indexes for a slow orders page

- Kind: learn
- Plan first: none needed
- Goal: explain how Postgres indexes work, why one helps, and when one does not
- Decision: whether an index is the right fix for the slow orders page
- Context: the orders page is slow. The query takes like 4 seconds. It filters orders by customer_id and sorts by created_at. The database is Postgres. You kind of know what a b-tree is (hedged)
- Must-haves:
  - explain why an index helps and when it does not
  - explain well enough to say it in standup
  - a small example you can run yourself (proof: a runnable script, run once)
  - investigate: why does an index help a query that filters by customer_id and sorts by created_at?
  - out of scope: moving to a different database
- Taste (flag, don't filter): plain words; shown by each term defined where first used
- Output: an explanation plus a short check of understanding and a runnable example; length unknown
- Verify: every claim names its source or the example run behind it, or says guess; the example run needs a Postgres instance
- If stuck: report only; never loosen a must-have without asking
- Skills:
  - explain-doc
  - how: single pass
- Parking lot: whether to move to a different database; everyone is talking about some new one
- Unknowns:
  - unknown: which Postgres version do you run?
  - unknown: how many rows are in the orders table?
  - unknown: where may the example run, a local Postgres or a scratch database?
  - unknown: what does "well enough for standup" mean, a one-minute talk or a longer one?

## Questions

1. Which Postgres version, and how many rows are in the orders table?
2. Where may the example run (local Postgres, scratch database)?
3. What does "well enough to explain in standup" mean to you?
