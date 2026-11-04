# Key: refund-endpoint

A synthetic case. The repo `acme/orders-api` and PR #214 are invented, and so is every line number below. The PR adds partial refunds to a Python web service. Never show this file to the skill.

The PR adds `POST /orders/{order_id}/refunds` in `app/routes/refunds.py`. It calls the payment provider through `app/payments/provider.py` and writes a ledger row through `app/payments/ledger.py`. Its body says "The nightly reconciliation job picks refunds up with no change." The ticket is PROJ-123, "Support staff can refund part of an order."

- acme/orders-api#214 at `0000000a1` (fake head)

## How to score

- Run `python3 check/score_case.py cases/refund-endpoint/key.md <drafts.md>`. It checks that each finding has a comment on the right path, within 3 lines of the row's Line when it names one. It also checks that the `Sites:` count reaches the minimum and that the comment names each `Terms:` word.
- A person then checks that each found comment names the same problem. Wording can differ.
- A comment with no evidence behind it is **unsupported** and counts as an error.
- The run passes the format only if `check/check_drafts.py` exits 0.

## Findings the skill should make

| ID | PR | Path | Line | Finding | Min sites | Proof |
|----|----|------|------|---------|-----------|-------|
| K1 | orders-api#214 | `app/routes/refunds.py` | 42 | The guard compares one refund to the order total, not to what is left after earlier refunds. Two refunds of 60.00 on a 100.00 order both pass. | - | A test that posts two partial refunds on one order gets 201 twice. |
| K2 | orders-api#214 | `app/payments/` | - | Dollar amounts become cents with `int(amount * 100)`, which truncates 19.99 to 1998. The same conversion sits in 4 places under `app/payments/`. | 4 | `git grep -n 'int(.*\* 100)' pr-214 -- app/payments/` lists 4 lines; `int(19.99 * 100)` prints 1998. |
| K3 | orders-api#214 | PR | - | The body says the nightly reconciliation job picks refunds up. `jobs/reconcile.py`, which the diff does not touch, selects only `kind == "charge"` rows, so refunds never reconcile. | - | `jobs/reconcile.py:18` at the PR head. |

Terms: K1 | refunded | total/remaining

Optional finds. A question or nit on these is fine, and missing them is not a miss.

- The new route has no rate limit, unlike the charge route next to it.
- The refund reason is free text with no length cap.

## Traps

- Saying the provider call has no idempotency key. It passes `idempotency_key=refund.id` on line 31 of `provider.py`.
- Saying the route lacks an auth check. The router is mounted under the staff-only dependency in `app/main.py`.
- Anchoring the cents finding on `app/routes/refunds.py`. The route takes cents already; the conversion is only under `app/payments/`.
