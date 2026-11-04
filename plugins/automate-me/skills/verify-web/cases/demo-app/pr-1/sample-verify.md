# verify: example/demo-shop#1 fix: refund button now disables after one click to stop double refunds

PR: https://github.com/example/demo-shop/pull/1
Base: main 0000000aaaaaaa
Head: fix/refund-double-click 1111111bbbbbbb
App: http://127.0.0.1:8000 (demo)
Evidence: ~/.claude/verify-evidence/web/20261103-1400-pr-1
Doctor: base OK, head OK

## S1. One click on Refund disables the button
Claimed: "disables the Refund button after one click and relabels it Refunded" (body, test plan item 1)
Steps: admin, Reset demo data, click Refund once on order 1001, reload the order page
Base: the button stays enabled and still reads Refund. One refund row for order 1001.
Head: the button is disabled and reads Refunded. One refund row for order 1001.
Evidence: doctor-base.txt, doctor-head.txt, s1-base-after.png, s1-head-after.png, s1-head-refunds.json
Verdict: VERIFIED

## S2. A double-click on Refund makes one refund
Claimed: "Double-click Refund on order 1002. Only one refund is made." (test plan item 2)
Steps: admin, Reset demo data, double-click Refund on order 1002, wait 2 s, open order 1002
Base: two refund rows, Refunded shows $39.98 on a $19.99 order.
Head: still two refund rows and $39.98. The button reads Refunded, so the screen looks fixed. The order page and GET /api/orders/1002/refunds both list two refunds.
Evidence: s2-base-order-page.png, s2-head-after.png, s2-head-order-page.png, s2-head-refunds.json
Verdict: CONTRADICTED

## S3. A read-only user sees no Refund button
Claimed: "A read-only user still sees no Refund button." (test plan item 3)
Steps: readonly persona, open Orders
Base: no Refund button on any row.
Head: no Refund button on any row. A POST to the refund URL as that user returns 403.
Evidence: s3-head-orders.png, s3-head-network.txt
Verdict: VERIFIED

Summary: 1 CONTRADICTED, 2 VERIFIED, 0 NOT RUN
