# PR review: partial refunds

Support staff can refund more than the customer paid, because each refund is checked alone. The cents conversion also loses a cent on common prices.

## acme/orders-api#214 | approve after the refund guard counts earlier refunds
About: Lets support staff refund part of an order, and records each refund in the ledger.
Changes: 6 files: 4 source, 2 test

### should fix | app/routes/refunds.py:44 | https://github.com/acme/orders-api/pull/214/files#diff-f509909fe0840cf32d1bc7e2fe77124136987f220f378d245e5e994584f85b7fR44
This compares the new refund to `order.total_cents` alone. Two refunds of 60.00 on a 100.00 order both pass. Can it compare against the total minus the amount already refunded?
Plain: Each refund is checked against the full order price, so several partial refunds can add up to more than the customer paid. Support staff would refund money the shop never received.
Evidence: A test posting two 60.00 refunds on one 100.00 order got 201 both times.
Step: measured | Staff posts a 60.00 refund on a 100.00 order; it returns 201.
Step: measured | Staff posts a second 60.00 refund on the same order; it returns 201.
Step: inferred | The provider pays out 120.00 against a 100.00 charge.

### should fix | app/payments/provider.py:27 | https://github.com/acme/orders-api/pull/214/files#diff-c5043bdf33e74b9cadd8252f7ffe86561e5997950350107e0a4a54ddf5d62971R27
`int(amount * 100)` truncates, so 19.99 becomes 1998 cents. Can this use `round()` or `Decimal` instead?
Plain: Floating-point math stores 19.99 as slightly less than 19.99, and `int()` drops the fraction. A customer refunded 19.99 gets 19.98, and the ledger disagrees with the provider by a cent.
Evidence: `python3 -c 'print(int(19.99 * 100))'` printed 1998.
Step: measured | A refund of 19.99 reaches `provider.refund()`.
Step: measured | `int(19.99 * 100)` gives 1998, so the provider refunds 19.98.
Sites: 4 | git grep -n 'int(.*\* 100)' pr-214 -- app/payments/

### should fix | app/payments/ledger.py:15 | https://github.com/acme/orders-api/pull/214/files#diff-374dfc4eb3698dfe00079d83af07963e72b80d21083ff919d5c7ad86e1781ceaR15
`int(amount * 100)` truncates, so 19.99 becomes 1998 cents. Can this use `round()` or `Decimal` instead?

### question | PR | https://github.com/acme/orders-api/pull/214
The body says the nightly reconciliation job picks refunds up. `jobs/reconcile.py` line 18 selects only `kind == "charge"` rows. Does it need a refund branch in this PR?
Plain: The nightly job that matches the ledger against the provider skips every row that is not a charge. Refunds would never be matched, so a failed payout goes unnoticed.
Evidence: `jobs/reconcile.py:18` at the PR head.

Body: The refund guard is the one change needed before merge. The other comments are inline.

## Totals
Refuter: checked 4, reworded 1, dropped 1.
