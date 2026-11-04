# Score: run-1

All inputs are invented. Scored by hand against key.md. The scorer also wrote the key.

## Blast radius (K1 to K10)

- Located: 10 of 10.
- Misread: 1. BR5 claims the LineItem photo-delete hook runs on an order delete. It does not, because BR2 deletes line items with a bulk query. The blast check passed, because the file and line were real.
- Incomplete: K6. The audit hook was found, but the null user in a background job was not mentioned.

## Hazards (H1 to H6)

- Found by the draft: H1 (hazard 2), H2 (hazard 1), H3 (hazard 3), H5 (hazard 4).
- Missed by the draft: H4 photo orphans (it repeated the BR5 misread), H6 audit noise and null user.
- Caught by the reviewer: H4, through WRONG BR and MISSED.

## Decisions

- Pending GAP 5, 8, 12 and 15 all listed with owner Product: 4 of 4.

## PM answers

- Followed: GAP 1, 3, 9, 11, 13.
- Contradiction found by the reviewer: a non-admin edit rides along on the next admin send, against GAP 9.

## Not in the key, found anyway

- Draft: request input can set crm_id and tenant_id. The update action has no admin check.
- Reviewer: the pull with no tenant context inserts duplicates. Not sending deletes means the pull recreates a deleted order. A missing notes key wipes local notes. Retries can reorder sends. The practice framework shares listener arrays across models.

## What changed in edd-mode because of this run

- Blast radius must describe each hook from its body, not its name.
- Playbook step 3 adds a second model that checks every BR against the code before drafting.
- The reviewer format now includes CONTRADICTS and WRONG BR lines.

## Outcome

- Every script check passed. The review failed 3 hazards and 1 decision, so the run stopped at step 6 as designed.
