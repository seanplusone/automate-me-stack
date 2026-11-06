# Key: learn-ramble

A synthetic case. The orders page and the query are invented. Never show this file to the skill.

This is a learn brief. Output is an explanation plus a check of understanding, and Verify is sources cited. The speaker never says which Postgres version, how many rows the table holds, or whether they may run anything against a real database. The brief must ask, not assume. Switching databases is a tangent.

## Facts, in the speaker's words

Fact: 4 seconds
Fact: customer_id
Fact: created_at
Fact: Postgres
Fact: standup

## Slots

Slot: Kind | learn
Slot: Goal | index
Slot: Output | explanation/explain | example | check/quiz
Slot: Verify | source/docs | cite
Slot: Must-haves | composite/multicolumn/two-column | customer_id | created_at
Slot: If stuck | report only/read-only/never create

## Gaps that must be asked, not guessed

Unknown: version | version
Unknown: data size | rows/table size/how big
Unknown: where to run | run/database/local

## Guesses that fail the run

Forbidden: version invented | \bpostgres(ql)?\s*(1[0-9]|9\.\d)\b
Forbidden: row count invented | \b\d[\d,.]*\s*(k|m|million|thousand)?\s*rows\b
Forbidden: index created on a real database | \bcreate index\b[^.\n]*\b(on prod|in prod|on staging|on the real)\b

## Parking lot

Parking: other database | database
