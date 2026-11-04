# Refund an order (demo app)

Covers: the orders list, the Refund button, the order page's refund history, and the read-only user.
Last driven: by `check/run_pr_case.js` on each run of the checks.

Start the app from `cases/demo-app/` as its `.claude/verify-web.yaml` says, then run the doctor
from that folder.

## Reach it
- Persona: `admin` (the default). For the read-only check, `readonly`.
- Path: sign in at `/login`. The app lands on Orders.

## Data
- Needs: the three seeded orders, 1001, 1002 and 1003, all `paid`, with $0.00 refunded.
- Reset: the **Reset demo data** button under the orders table (admin only). It reseeds all three.

## Drive
1. On Orders, find the row for the order and its **Refund** button.
2. Click **Refund** once. For the double-refund check, double-click it instead.
3. Wait for the status message above the table, and for the row's Status to read `refunded`.
4. Open the order by its number, to see its Refunds list.

## Prove
- On screen: the message "Refunded $<amount> on order <id>", Status `refunded`, and Refunded equal
  to the order amount. A Refunded value of twice the amount is a double refund.
- Second way: the order page's Refunds list after a fresh load, or the read-only
  `GET /api/orders/<id>/refunds` with the signed-in session. One row per refund.
- Read-only user: no Refund button on any row, and a POST to `/orders/<id>/refund` returns 403.
- Known noise: none. Any console error is a finding.

## Clean up
- Click **Reset demo data**. Nothing else persists outside the app's data folder.
