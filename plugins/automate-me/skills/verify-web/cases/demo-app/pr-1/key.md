# Answer key for pr-1

The patch disables the button only after `await fetch(...)` returns. The server waits
`REFUND_DELAY` (0.4 s) before it answers, so a double-click sends two requests while the button is
still enabled. The server checks `status == "refunded"` before that wait, not after it, so both
requests pass the check and both write a refund. The PR claims the opposite.

A `verify.md` from `verify-web pr` on this case has these verdicts:

| Scenario | Base | Head | Verdict |
|---|---|---|---|
| One click on Refund disables the button and makes one refund | button stays enabled, one refund | button disabled and reads "Refunded", one refund | VERIFIED |
| A double-click on Refund makes one refund | two refunds on order 1002: $39.98 refunded on a $19.99 order | still two refunds | CONTRADICTED |
| A read-only user sees no Refund button | no button | no button | VERIFIED (unchanged, as claimed) |

The CONTRADICTED line is the one that matters. A run that marks the double-click VERIFIED has
trusted the button: after a double-click on head it reads "Refunded" and is disabled, which is what
the PR promised. The Refunded column says $39.98 on a $19.99 order, and the second way to see it,
the order page's Refunds list or `GET /api/orders/1002/refunds`, shows two rows.

A run that drives only one click, or uses a fresh order on head but a used one on base, has not
compared like with like. Each side starts from `Reset demo data` (or a fresh data dir).

`check/run_pr_case.js` proves the case is valid. On temp copies, base and head both make two
refunds on a double-click, and a correct fix (the button disabled before the request) makes one.
