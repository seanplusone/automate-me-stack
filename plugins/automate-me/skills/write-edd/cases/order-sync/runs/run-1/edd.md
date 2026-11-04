# EDD: Send Order Changes Back to the CRM

**Epic:** TBD
**PRD:** Send Order Changes Back to the CRM
**Status:** Draft
**App:** repo

## Summary

Today the app pulls orders from CRM. This change sends edits made in the app back to CRM, so both places match.

- An admin saves an order in the app. The app saves it as it does now, then queues a send of `status` and `notes` to CRM. The send runs within a minute and does not block the save [R1] [R2] [GAP 1] [GAP 3] [GAP 4].
- A save by a non-admin stays in the app and is not sent [R5] [GAP 9].
- An admin delete is queued as a delete in CRM. This is blocked on a Product answer [R4].
- A failed send is retried, then marked failed and shown to the user [R7] [GAP 2].
- An admin starts the first load of existing orders. It never overwrites a value already in CRM [R6] [GAP 10] [GAP 11].
- Reports may differ from CRM for a short time, and during failures [R8] [GAP 13].
- The existing pull stays as it is. CRM wins when the pull runs [R3] [GAP 6].

The send is triggered from the controller, not from a model event. A model event would fire for the pull's own writes and create a loop.

Four Product questions are open (GAP 5, 8, 12, 15). Each is a row in Decisions blocking build start. The launch target is the end of next month for the first three customers. No slice below has a date.

## Architecture

The map has four branches. Each is a component.

**CRM.** The remote system. It receives updates and deletes. Whether it reports success or failure is unconfirmed [GAP 14].

**app.** Two parts change.
- `OrdersController` decides, after a save or delete, whether to queue a send. It checks that the user is an admin [R5].
- The order screen shows the sync state of the last send [R7].

**Between.** Four parts.
- An outbox table `crm_outbox` (new) holds one row per pending send. The row is the to-do list. It carries the values to send, so nothing is read back from the model at send time.
- A send job (new) reads due outbox rows and calls CRM through a CRM client (new). It retries and records the result.
- A backfill command (new) fills the outbox for the first load [R6].
- `CrmPull` is unchanged. It keeps writing CRM values into the app [R3].

**Result.** Reports keep reading the local table. `OrderReport` is unchanged [R8].

Flow for one admin save:
1. `OrdersController::update` loads the order, fills it and saves it.
2. The save fires the existing hooks. The controller then adds one outbox row if `status` or `notes` changed.
3. The send job picks up the row and calls CRM.
4. The job marks the row sent, or schedules a retry, or marks it failed.

## Data model

The change writes two entities.

**`crm_outbox` (new table).**
- `id`, `tenant_id`, `order_id`, `crm_id`.
- `operation`, either update or delete.
- `payload`, a JSON copy of `status` and `notes` taken at save time. Empty for delete.
- `state`: pending, sent or failed.
- `attempts`, `next_attempt_at`, `last_error`.
- `created_by` (the user id), `created_at`, `sent_at`.
- Indexes on `tenant_id` and on `state` with `next_attempt_at`. No foreign keys.
- `tenant_id` and `crm_id` are stored on the row. A delete send must work after the order row is gone, and the job has no tenant context of its own [BR3] [BR7].

**`Order`.** No new column. Sync state lives in the outbox so the columns the pull owns stay as they are [BR10]. The sync state shown on screen is read from the newest outbox row for the order.

`AuditLog` is written by the existing save hook for app saves [BR4]. The send job writes no audit row.

Rows with no `crm_id` are skipped. App-created orders are covered by a Decision.

## Backend

### Contracts

**1. Controller to outbox, on save [R1] [R5] [GAP 1] [GAP 3] [GAP 9].**
- Caller: `OrdersController::update`. It writes one outbox row.
- Input: tenant, order id, the `crm_id` loaded before `fill` runs, and the new `status` and `notes`.
- Only admins queue. A non-admin save is saved and not queued.
- No row is written if `status` and `notes` did not change.
- If the outbox write fails, the save has already happened. The controller logs the failure and the user sees an error [R7].
- The controller reads `crm_id` before `fill`. The model lists `crm_id` and `tenant_id` as fillable, so request input could otherwise change the target [BR8].

**2. Send job to CRM [R1] [R2] [GAP 2] [GAP 14].**
- Caller: the send job (new), run by a queue worker.
- It sets the tenant context from the row before any model query [BR7].
- It sends the payload on the row. It never reloads the order.
- On success it marks the row sent.
- On a retryable failure it adds to `attempts` and sets `next_attempt_at`. After the last attempt it marks the row failed and stores `last_error`.
- The retry rule is a Decision.
- Whether CRM returns a clear success or error is unverified. See Unverified below.
- The first attempt runs within one minute of the save. This needs a worker that polls at least once a minute, which is unverified.

**3. Controller to outbox, on delete [R4].**
- Caller: `OrdersController::destroy`. It writes a delete row with `crm_id` and `tenant_id` before it deletes.
- Existing hooks run as now. The delete removes line items and their photos first [BR2] [BR5] [BR9].
- This contract is built only after the delete Decision is answered.

**4. Pull and the new send [R3] [GAP 5] [GAP 6] [GAP 7].**
- `CrmPull::run` is called with a tenant and a list of records. It matches rows by `crm_id` and tenant, then overwrites `site_name`, `status`, `notes` and `ordered_at` [BR10] [BR18].
- It does not read the outbox. It does not know about unsent edits.
- Answer to GAP 6: the pull does read back what the app sent, because it overwrites every field on every run. It cannot loop, because the send is not triggered by model events. It can overwrite an app edit that is still queued. See hazard 2.
- Answer to GAP 7: the repo shows no caller and no schedule for `CrmPull::run`. Whether the pull is instant or scheduled is unverified. PROBE1 is proposed.
- Which clock decides "newest" is a Decision.

**5. First load [R6] [GAP 10] [GAP 11].**
- Caller: an admin runs the backfill command (new) for one tenant.
- It walks that tenant's orders in id order, in batches. The batch size and the pause between batches are settings.
- It writes one outbox row per order that has an `crm_id`.
- Rows already queued or sent for the same order are skipped, so a rerun resumes where it stopped.
- Each send first checks CRM. If the field already holds a value, the send skips it. This follows the PM answer to not overwrite anything already in CRM.
- CRM rate limits are unverified. Batch size and pause are set after SPIKE2.
- Whether CRM can check and update in one call is unverified. See SPIKE3.

### Unchanged code

The change leaves these as they are.
- The saving hook that recomputes `score` [BR1] [BR12] [BR17]. `score` is not sent.
- The delete hook that removes line items [BR2] [BR5].
- The boot step that registers each trait's hooks [BR6]. The new outbox model adds no trait.
- The tenant fill on create and the tenant scope [BR3] [BR7] [BR13]. The send job works around the scope with the stored `tenant_id`.
- The audit hook [BR4] [BR16].
- The controller's lookup by id [BR14].
- The report count by status [BR15]. Under Reading A it can differ from CRM for a short time and during failures [GAP 13].
- The pull's match on `crm_id` and tenant [BR18].
- The CSV import [BR11]. It inserts with raw SQL, bypasses every hook, and never queues a send. See hazard 4.

## Frontend

The repo holds no frontend code, so this section describes the data the screen needs. No screen component is named.

- The order response carries a sync state: none, pending, sent or failed [R7].
- A failed state carries a short message. The wording, the audience and a retry button are open [GAP 12].
- A non-admin sees no sync state, because nothing was queued for them [R5].
- The backfill is run by an admin. Whether it needs a screen or only a command is open.

## Testing

No test directory exists in repo. These are the cases to cover, each written to fail if the behavior is removed.

- An admin save of `status` queues one update row with `status` and `notes` only [R1].
- A non-admin save changes the order and queues nothing [R5].
- A save that changes neither `status` nor `notes` queues nothing.
- A request that sets `crm_id` or `tenant_id` does not change where the row is sent.
- A run of `CrmPull::run` queues nothing [R3].
- The send job runs with no tenant context set, and still sends the right tenant's row [BR7].
- A delete row is sent after the order and its line items are gone [R4].
- A failed send retries by the chosen rule, then the state is failed [R7].
- The backfill resumes after a stop and sends no duplicate.
- The backfill does not overwrite a value already in CRM [R6].
- Scenario 1, an app-created order with no `crm_id`, is skipped by default.
- The one-minute limit is measured in a test environment with a real worker [R1].

## Known hazards

| # | Hazard | Evidence | Mitigation |
|---|--------|----------|------------|
| 1 | A send triggered by a model event also fires for the pull's writes. The pull saves, the app sends to CRM, the pull reads it back, and it repeats. | BR10, BR4, src/Sync/CrmPull.php:12 | Trigger the send only from the controller [BR8] [BR9]. The pull and the CSV import never queue. |
| 2 | The pull overwrites an app edit while its send is still queued. CRM then holds the old value, or the job sends it back later. | src/Sync/CrmPull.php:12, BR10 | The row carries the saved values, so the job sends the app edit. The next pull then matches. Which side wins is a Decision. |
| 3 | The send job has no tenant context. The tenant scope then matches nothing or the wrong tenant. | BR7, BR3 | The outbox row stores `tenant_id`. The job sets the tenant before any model query. |
| 4 | The CSV import inserts rows with raw SQL. They get no `tenant_id`, no `crm_id`, and no outbox row. | BR11, src/Console/ImportCsv.php:14 | Unchanged. Imported rows are not sent. They have no `crm_id`, so the backfill skips them too. |
| 5 | The delete send cannot load the order, because the row and its line items are gone. | BR9, BR2, BR5 | The delete row stores `crm_id` and `tenant_id` before the delete runs. |
| 6 | Request input can set `crm_id` or `tenant_id`, because both are fillable. The send could then target another record. | src/Http/OrdersController.php:12, src/Models/Order.php:14 | The controller reads `crm_id` and tenant before `fill`. |
| 7 | The update action has no admin check today. R5 needs one. | src/Http/OrdersController.php:9 | Add an admin check that gates only the queueing. The save is not blocked, per Reading A. |
| 8 | A save fires the audit hook with the dirty fields. The controller sees no dirty fields after the save. | BR16, BR4 | Compare `status` and `notes` against the loaded values before the save. |
| 9 | Reports differ from CRM while a send is pending or failed. | BR15 | Accepted under Reading A [GAP 13]. The sync state is visible on the order. |

### Unverified

These claims have no evidence yet. Each names the probe or spike that would settle it.

- CRM returns a clear success or error for an update [GAP 14]. SPIKE1 would call the CRM sandbox with a good update and a bad one and record both responses.
- CRM rate limits for a first load of several thousand updates [GAP 10]. SPIKE2 would send a measured batch to the sandbox and record the limit responses.
- CRM can check and update in one call, so the no-overwrite rule costs one call per order [GAP 11]. SPIKE3 would try a conditional update in the sandbox.
- The existing pull is instant or on a schedule [GAP 7]. PROBE1 would read the caller and the schedule outside this repo, and record the interval.
- A worker polls at least once a minute, so the one-minute limit holds [GAP 1]. PROBE2 would read the worker settings and time a queued job.
- The pull reads CRM edit time, so a latest-timestamp rule is possible [GAP 5]. PROBE3 would read a sample record.

## Decisions blocking build start

| # | Decision | Options | Owner | Default |
|---|----------|---------|-------|---------|
| 1 | Which edit is newest when the pull and an app edit disagree [GAP 5] [R3]. | A: CRM wins. B: the later timestamp wins. Evidence that settles it is PROBE3 and a Product answer. | Product | Do A, which is how the pull works today. If Product picks B, add the compare to the pull after PROBE3 shows CRM sends an edit time. |
| 2 | Whether a delete is permanent in CRM, and who may delete [GAP 8] [R4]. | A: hard delete in CRM. B: mark the record deleted in CRM. C: do not send deletes. | Product | Do C. If Product confirms a permanent delete by admins only, build contract 3 with A. |
| 3 | Which failures show a message, its wording, who sees it, and whether the user retries [GAP 12] [R7]. | A: the saving user sees it on the next load. B: all admins see a failed list. C: A and B together. | Product | Do A with the stored `last_error` text kept internal. If Product wants a retry button, add one that requeues the failed row. |
| 4 | Which edit wins when two people edit the same order [GAP 15]. | A: last save wins. B: reject the stale save. C: merge by field. | Product | Do A, which is what the app does today. If Product picks B, add a version check to `OrdersController::update`. |
| 5 | What happens when CRM is unreachable or rejects a send [GAP 2] [R1]. | A: retry a fixed number of times, then fail. B: retry until it succeeds. C: drop the change and log it. SPIKE1 would show which errors are permanent. | Engineer | Do A with 3 attempts, at 1, 5 and 15 minutes after the failure. If SPIKE1 shows a permanent error code, mark that row failed with no retry. |
| 6 | Which values the job sends [GAP 6] [R3]. | A: values stored on the outbox row at save time. B: current values read from the order at send time. | Engineer | Do A. If Product picks the CRM-wins rule and wants the app edit dropped when the pull ran first, do B. |
| 7 | Whether an app-created order with no `crm_id` is created in CRM (Scenario 1). | A: skip it. B: create it in CRM and store the returned id. | Product | Do A. If Product answers B, add a create operation after SPIKE1 shows what CRM returns. |

## Delivery slicing

Each slice can ship behind a setting that is off by default.

1. **Outbox and send job.** The table, the CRM client (new), the job, retries and failed state. No trigger yet. Tested against a fake CRM [GAP 2] [GAP 14].
2. **Update on save.** The admin check, the change comparison, and the outbox write in the controller [R1] [R5].
3. **Sync state on the order.** The state field and the failed message. The message wording waits on Decision 3 [R7].
4. **Delete.** Waits on Decision 2 [R4].
5. **First load.** The backfill command. Waits on SPIKE2, SPIKE3 and an admin runbook [R6] [GAP 10] [GAP 11].

Slices 1 and 2 do not depend on a Product answer. The launch target is the end of next month for three customers.
