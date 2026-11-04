# EDD: Send Order Changes Back to the CRM

Epic: TBD
PRD: Send Order Changes Back to the CRM
Status: Draft
App: repo

## Summary

Today the app pulls orders created in CRM. This design sends order changes from the app to CRM, so both places match.

- An admin saves an order. The app queues a change and a job sends it to CRM within a minute [R1, R2, R5].
- An admin deletes an order. The app queues a delete message for CRM [R4].
- The first time a customer turns this on, an admin starts a one-time send of all that customer's orders [R6].
- The pull from CRM stays, with one guard so it cannot overwrite an edit that was not sent yet [R3].
- A failed send shows the user an error [R7].
- Reports keep reading the app database and match CRM after the short delay the PM accepted [R8].

Out of scope are photos, attachments and the mobile app. The launch target is the end of next month for three customers (PRD point U4). Nothing in this draft is approved.

## Architecture

- [A1] Store each outgoing change as a row in the existing outbox and deliver it to CRM from the existing delivery job. This reuses `WebhookOutbox` and `DeliverWebhooks`, which already hold the target, payload, status, attempts and last error. The house rule in `.claude/rules/jobs.md` says outgoing messages are rows first and a job delivers them in id order. Serves [R1, R2].
- [A2] Capture each app save and delete as an outgoing row. The saved hook in `Auditable` is the closest precedent, but it would also fire on pull writes [BR9]. The capture point is Decision 1.
- [A3] Send only changes saved by admins. No code checks for an admin today, so this is new. The check point is Decision 2.
- [A4] A delete is one more outgoing message. It uses the same outbox and job as [A1]. Whether the delete is permanent is Decision 7.
- [A5] An admin starts a one-time send in batches. `ImportCsv` is the precedent for operator-started bulk work, but nothing batches, throttles or resumes today. The shape is Decision 3.
- [A6] Keep the existing pull. It already writes CRM values by CRM id in `CrmPull`. The conflict rule waits on Decisions 6 and 8.
- [A7] Tell the user when a change does not reach CRM. The outbox keeps the failure in last_error, but nothing shows it. The display is Decision 4.
- [A8] Reports keep reading the app database, as `OrderReport` does today. They match CRM once delivery finishes.
- [A9] Know each customer's CRM address. The pull receives its records from a caller outside this repo, and no code stores an address. The storage is Decision 5.

## Data model

- [D3] The payload of an outgoing row for CRM holds only status and notes. BECAUSE ANSWER GAP 3. The order score is not sent.
- [E1] Each outgoing row sets its own customer id when it is written. `WebhookOutbox` does not fill it in. NEEDED BECAUSE CS16.
- [E3] Add an order id column to the outbox, with an index. The outbox row has no order id today. NEEDED BECAUSE CS15.
- [E4] Add a saving user id column to the outbox. NEEDED BECAUSE CS15.
- [D10] Store each customer's CRM address and copy it into the row's target address when the row is written. BECAUSE R1. The options are in Decision 5.
- The order table gets no new column. It has no edit time today, which matters for Decisions 6 and 8.

## Backend

- [D1] After an update saves in `OrdersController`, queue one outgoing row with the CRM id, status and notes. BECAUSE R1. This is the only user update path [BR7]. Where the row is written is Decision 1.
- [D2] After a delete succeeds in `OrdersController`, queue a delete message. BECAUSE R4. This is the only user delete path [BR8].
- [D6] Queue a row only when the saving user is an admin. Other saves stay in the app. BECAUSE ANSWER GAP 9. The user data in use today is the user id only.
- [D4] Run `DeliverWebhooks` for each customer every minute. BECAUSE ANSWER GAP 1. A queued row is first sent within a minute of the save.
- [D5] Answers [GAP 2]. A reply that is not OK leaves the row pending until its attempts reach 3. Then the job marks it failed and keeps the reply as the error. BECAUSE GAP 2. Today the job marks a row failed after one bad reply and never loads it again.
- [E1] Load only the running customer's pending rows in `DeliverWebhooks`. NEEDED BECAUSE CS16.
- [E2] Answers [GAP 10]. Load a limited number of pending rows per run, oldest first, so a first send of several thousand rows does not load at once. NEEDED BECAUSE CS16. CRM rate limits are unverified, so the page size is set after the spike in Decision 10.
- [D7] Add an admin command, `SendOrdersToCrm` (new), that takes a customer id and queues one row per order CRM does not already hold. BECAUSE ANSWER GAP 11. An admin starts it and it overwrites nothing in CRM. What "already hold" means is Decision 3.
- [D8] Answers [GAP 6]. `CrmPull` skips any order that has a pending outgoing row, so it cannot overwrite an edit that was not sent. BECAUSE GAP 6. This needs the order id from [E3]. The pull writes through save, so it also fires the audit and score hooks [BR9].
- [D9] Record a failure so the user can see it. BECAUSE R7. The row keeps the error, the saving user [E4] and the order [E3].
- [D11] No change to `OrderReport`. BECAUSE ANSWER GAP 13, which accepts a short delay. It reads status under the customer filter [BR12].
- Answers [GAP 7]. The repo does not show how often the pull runs, because nothing in it calls `CrmPull`. See Decision 9.
- Answers [GAP 14]. Whether CRM reports success or failure is unverified. See hazard 6 and Decision 10.

## Frontend

- [D9] The order page shows the status of its latest change to CRM. BECAUSE R7. The repo has no view files, so this entry follows Decision 4 and the page code outside the repo.
- Every other point has no frontend change. Reports keep their current screen [R8].

## Testing

The repo has no test files today. Each test below fails if its change is reverted.

- [D1, D6] An admin update queues one row with status and notes only. A non-admin update queues none.
- [D2] A delete queues one delete message.
- [D4, D5, E1] The job sends only the running customer's rows. A bad reply leaves the row pending until the third attempt, then marks it failed.
- [E2, D7] A customer with more rows than one page is sent over several runs and no row is sent twice.
- [D8] A pull of an order with a pending row leaves the app values unchanged. A pull of one without a pending row writes the CRM values.
- [D9] A failed row shows its error to the user who saved.
- Reports. A report counts the same open orders before and after this change [R8].
- A spike against a sandbox CRM settles hazard 6 before any send test counts as proof.

## Known hazards

| # | Hazard | Evidence | Level | Mitigation |
|---|--------|----------|-------|------------|
| 1 | The pull replaces site name, status, notes and order date with the CRM values. An app edit waiting in the outbox is overwritten before it is sent. | src/Sync/CrmPull.php:12, BR9, CS13 | 3 | [D8] skips orders with a pending row. |
| 2 | A hook-based capture would also fire on pull writes and send CRM values back to CRM. | BR9, CS14, src/Traits/Auditable.php:12 | 3 | Decision 1 defaults to writing the row in the controller. |
| 3 | Rows added by the CSV import never reach CRM. The import skips the model, so no hook runs, and it sets no CRM id. | BR10, src/Console/ImportCsv.php:14 | 2 | Decision 11. |
| 4 | The delivery job loads pending rows for every customer in one query. A first send of several thousand rows loads all at once. | CS16, src/Jobs/DeliverWebhooks.php:18 | 2 | [E1] and [E2]. |
| 5 | The job marks a row failed after one bad reply and never loads it again, so one blip loses the change. | CS18, src/Jobs/DeliverWebhooks.php:22 | 3 | [D5] retries up to 3 attempts. |
| 6 | The job counts a reply as success when ok() is true. If CRM answers OK but rejects the change, the row is marked sent and the two places differ. | CS18, src/Jobs/DeliverWebhooks.php:22 | 2 | Run the spike in Decision 10 before build. |
| 7 | The existing pull may insert duplicates. It never sets the customer context, so the customer filter can match nothing. The PRD assumes the pull already works [R3]. | CS13, BR6, src/Traits/TenantScoped.php:12 | 3 | Ask the owner of the pull's caller to confirm the context is set. See Decision 9. |
| 8 | A delete in the app that does not reach CRM is brought back by the next pull, which creates a new order. | CS13, BR8, src/Sync/CrmPull.php:12 | 3 | Decisions 7 and 12. |
| 9 | The save can succeed while writing the outgoing row fails, so the change is lost. The controller has no error handling. | CS4, src/Http/OrdersController.php:13 | 3 | Write the row in the same database transaction as the save. Confirm the framework supports it. |

The whole design depends on one fact. CRM must report success or failure of an update (hazard 6, [GAP 14]). It is at level 2 and cannot reach level 4 yet. A spike would settle it. Send one status and notes update, one accepted and one rejected, to a sandbox CRM account and record both replies. Name it SPIKE1 when it exists.

Unchanged by this design, and still true [BR1, BR2, BR3, BR4, BR5, BR11, BR13, BR14, BR15].

- Every save still recalculates the score and writes an audit row.
- Deletes still skip the audit and still leave line item photos in storage.
- The customer filter and model boot still work as they do today.
- The controller still loads an order under the customer filter before an update.

## Decisions blocking build start

| # | Decision | Options | Owner | Default |
|---|----------|---------|-------|---------|
| 1 | Where the outgoing row is written [A2]. | A2.1 saved and deleting hooks on the order, with the pull turned off while it writes. A2.2 the update and destroy actions in the controller. | Engineering | Do A2.2. If a third user write path appears before build, do A2.1. |
| 2 | How the app knows a user is an admin, and where the rule is applied [A3]. | A3.1 ask when writing the row and write none for non-admins. A3.2 write every row with the role and let the job skip non-admins. | Engineering | Do A3.1. If Product wants unsent changes kept, do A3.2. |
| 3 | The shape of the first send [A5], and what "CRM already holds" means [R6]. | A5.1 a command writes rows and the delivery job drains them. A5.2 a dedicated job posts batches directly. Holds means (a) the order has a CRM id, or (b) CRM has a value in the field. | Product | Do A5.1 and read "holds" as (a). If Product says (b), ask for a way to read CRM values first. |
| 4 | Which failures show a message, what it says, who sees it, and whether the user can retry [R7, GAP 12]. PENDING. | A7.1 the order page shows the latest status with a retry action. A7.2 the job notifies the user who saved. | Product | Do A7.1 without retry. If Product asks for retry or a notice, add it after the status shows. |
| 5 | Where the CRM address and the way to sign in to CRM are stored [A9]. No code stores either today. | A9.1 store per customer and copy to the row. A9.2 the job looks it up at send time. | Engineering | Do A9.1. If the spike in Decision 10 shows a token that expires, do A9.2 for the token only. |
| 6 | Which edit is newest when CRM and the app differ [R3, GAP 5]. PENDING. | CRM edit wins. Latest timestamp wins, which needs an edit time the app does not store. | Product | Do CRM wins on every pull, as the pull works today. If Product picks latest timestamp, add an edit time to the order. |
| 7 | Whether a delete in CRM is permanent, and who may delete [R4, GAP 8]. PENDING. | Remove the record in CRM. Mark it deleted in CRM and keep it recoverable. | Product | Do remove it, as R4 says. If Product wants recovery, mark it deleted instead. |
| 8 | What happens when two people edit the same order [GAP 15]. PENDING. | Last save wins. Merge by field. Warn the second person. | Product | Do last save wins, as the save works today. If Product wants a warning, add an edit time check. |
| 9 | How often the pull runs, and who sets the customer context before it runs [GAP 7]. The caller is outside this repo. | Read the caller outside this repo. Add a schedule in this repo. | Engineering | Do read the caller. If it does not set the context, raise it with Product as a separate fix. |
| 10 | Whether CRM reports success or failure, and its rate limits [GAP 14, GAP 10]. Unverified. | Run a spike against a sandbox CRM account. Read the CRM documentation only. | Engineering | Do the spike. If no sandbox exists, build with ok() and mark the risk open. |
| 11 | Whether orders with no CRM id, such as CSV imports, are created in CRM [CS10]. | Do not create them and send updates only for orders with a CRM id. Create them with a new create message. | Product | Do not create them. If Product wants them, add a create message. |
| 12 | Whether the next pull may bring back an order the app deleted [CS13]. | The pull skips CRM ids the app deleted. The pull recreates them. | Product | Do skip them. If the pull must stay as it is, accept the recreate and document it. |

## Delivery slicing

- Slice 1. The spike in Decision 10 and Decisions 1, 2 and 5. Nothing else starts before the spike answers.
- Slice 2. The outbox and job changes [D3, D4, D5, E1, D10, E3, E4].
- Slice 3. The queue points for updates and deletes [D1, D2, D6].
- Slice 4. The pull guard [D8].
- Slice 5. The first send [D7, E2].
- Slice 6. The error message [D9].
- Reports need no slice [D11].
