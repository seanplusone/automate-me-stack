HAZARD 1 | PASS | CrmPull.php:12 saves through the model and fires the saving and saved hooks, and sending only from the controller is a concrete fix.
HAZARD 2 | FAIL | The mitigation hands the outcome to a Decision, and it conflicts with Decision 1: under "CRM wins" a queued stale payload still overwrites a newer CRM edit after the pull.
HAZARD 3 | PASS | TenantScoped.php:12 scopes every query to Context::tenantId(), and storing tenant_id on the row and setting context first is concrete.
HAZARD 4 | PASS | ImportCsv.php:14 inserts with raw SQL and no tenant_id or crm_id, and the doc states plainly that these rows are not sent.
HAZARD 5 | PASS | The delete at OrdersController.php:19 removes the row, and storing crm_id and tenant_id before the delete is concrete.
HAZARD 6 | FAIL | Reading crm_id before fill only protects one send, because fill at OrdersController.php:12 still saves the new crm_id and tenant_id, so later sends and the pull match at CrmPull.php:13 use the changed values.
HAZARD 7 | PASS | update at OrdersController.php:9 has no admin check, and gating only the queueing matches the GAP 9 answer.
HAZARD 8 | FAIL | BR4 and BR16 show the audit hook reads dirty fields, but nothing in the repo shows dirty state after save, because Model.php has no save method.
HAZARD 9 | PASS | OrderReport.php:11 reads the local table, and the GAP 13 answer accepts a short delay.
DECISION 1 | PASS | The default is "Do A. If Product picks B, add the compare after PROBE3."
DECISION 2 | PASS | The default is "Do C. If Product confirms a permanent admin-only delete, build contract 3 with A."
DECISION 3 | PASS | The default is "Do A. If Product wants a retry button, requeue the failed row."
DECISION 4 | PASS | The default is "Do A. If Product picks B, add a version check."
DECISION 5 | PASS | The default is "Do A with 3 attempts at 1, 5 and 15 minutes. If SPIKE1 shows a permanent error code, fail with no retry."
DECISION 6 | FAIL | The default sends stored values, which overrides the "CRM wins" default of Decision 1, and the "If" branch names a condition that is already Decision 1's default.
DECISION 7 | PASS | The default is "Do A. If Product answers B, add a create operation after SPIKE1."
MISSED | The pull runs under the tenant scope. With no tenant context, the updateOrCreate lookup matches nothing and inserts a duplicate on every run, so one crm_id can end up on several rows. | src/Sync/CrmPull.php:12, src/Traits/TenantScoped.php:12
MISSED | $listeners and $scopes are declared only on the abstract Model, so static:: writes to one shared array. The tenant scope and the Order hooks register for every model, including LineItem, AuditLog and the new outbox model. The send job would then read no outbox rows without a tenant context. | src/Framework/Model.php:7, src/Framework/Model.php:8, src/Framework/Model.php:24
MISSED | Under Decision 2's default (no delete sent), the next pull recreates an order the app deleted, because updateOrCreate inserts when no row matches. | src/Sync/CrmPull.php:12, src/Http/OrdersController.php:19
MISSED | The pull writes notes as null when the CRM record has no notes key. This wipes the app value, and the next admin save sends null notes to CRM. | src/Sync/CrmPull.php:17
MISSED | Line items are removed with a query delete, so the LineItem deleting hook never runs and photos stay in storage. The doc says photos are removed first. | src/Models/Order.php:25, src/Models/LineItem.php:16
MISSED | Retries can reorder sends. A row that fails and retries at 15 minutes can land after a newer row for the same order, so CRM ends up with the older payload. No per-order ordering is stated. | Decision 5, GAP 2
NAMES | None found. Every existing class, method and field named in the doc exists in repo/src, and new parts are marked (new).
CONTRADICTS | Contract 1 and Decision 6 put both status and notes on every admin payload, so a non-admin's earlier change to the other field goes to CRM on the next admin save. | GAP 9
WRONG BR | BR5 | src/Models/Order.php:25 calls lineItems()->delete(), a query delete, so the hook at src/Models/LineItem.php:16 does not run for those line items.
WRONG BR | BR9 | src/Http/OrdersController.php:19 fires BR2 only. BR5 does not fire, for the reason above.
WRONG BR | BR10 | src/Sync/CrmPull.php:12 also writes tenant_id and sets notes to null when the key is missing (line 17). BR3 does nothing here because tenant_id is passed. The lookup also runs under SCOPE BR7.
WRONG BR | BR18 | src/Sync/CrmPull.php:13 is not the only match condition. SCOPE BR7 adds tenant_id equal to Context::tenantId() (src/Traits/TenantScoped.php:12), so the match fails with no context.
WRONG BR | BR15 | src/Reports/OrderReport.php:11 counts only rows with status 'open'. It does not count by status in general.
