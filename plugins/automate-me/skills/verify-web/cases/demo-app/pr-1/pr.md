# Synthetic PR 1 for the demo app

Use this as the `gh pr view` output when you practise `verify-web pr` on the demo app. The diff is
`fix.patch`, applied to `../app.py`. Nothing here exists on GitHub.

- Number: 1 (invented)
- Base: `main`. Head: `fix/refund-double-click`.
- Title: fix: refund button now disables after one click to stop double refunds

## Body

Support reported orders refunded twice. An admin double-clicks Refund on the orders page, and the
customer gets the money back twice.

This change disables the Refund button after one click and relabels it "Refunded", so a second
click does nothing.

## Test plan

- [x] Click Refund once on order 1001. The button turns grey and reads "Refunded".
- [x] Double-click Refund on order 1002. Only one refund is made.
- [x] A read-only user still sees no Refund button.
