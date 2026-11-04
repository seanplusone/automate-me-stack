# Key: order-sync

The planted traps in `repo/` and what a good EDD must do with them. Never show this file to the skill.

The repo, the PM answers and this key are invented. Entity under change: `Order`.

## Blast radius the skill should find

| ID | Kind | Where | What it does |
| --- | --- | --- | --- |
| K1 | hook | `src/Models/Order.php` saving | Recomputes `score` from line items on every save |
| K2 | hook | `src/Models/Order.php` deleting | Bulk deletes line items with a query, so each LineItem's own deleting hook never runs |
| K3 | hook | `src/Models/LineItem.php` deleting | Deletes the photo file. Skipped by K2, so photos are orphaned |
| K4 | hook | `src/Traits/TenantScoped.php` creating | Sets `tenant_id` from request context. A background job may have no tenant |
| K5 | scope | `src/Traits/TenantScoped.php` addGlobalScope | Filters every query by current tenant. A job without a tenant matches nothing or the wrong rows |
| K6 | hook | `src/Traits/Auditable.php` saved | Writes an AuditLog row with `Auth::id()`. Null in a job, and every pull or send writes audit rows |
| K7 | writer | `src/Sync/CrmPull.php` updateOrCreate | Overwrites status and notes from CRM on every pull, so local edits are lost |
| K8 | writer | `src/Console/ImportCsv.php` DB::table insert | Raw insert. Skips every hook and the tenant scope, so rows have no tenant_id |
| K9 | writer | `src/Http/OrdersController.php` update and destroy | The user edit and delete paths the feature hooks into |
| K10 | reader | `src/Reports/OrderReport.php` | Reads `status`, scoped by tenant |

## Hazards a good EDD must raise

| ID | Hazard | Built from |
| --- | --- | --- |
| H1 | Pull overwrites local edits before they are sent. Status and notes are the PM's chosen fields (GAP 3) | K7, GAP 3 |
| H2 | Send and pull loop: a send triggers a save, the pull writes back, which counts as a new change | K7, K6, GAP 6 |
| H3 | The send job runs without a tenant, so the scope or the creating hook misbehaves | K4, K5 |
| H4 | Deletes orphan line item photos, and the delete must also reach CRM (GAP 8 pending) | K2, K3 |
| H5 | CSV import rows bypass hooks, so they never trigger a send and have no tenant | K8 |
| H6 | Audit log fills with sync writes attributed to no user | K6 |

## Decisions a good EDD must list

Pending PM answers become decisions owned by Product: GAP 5, GAP 8, GAP 12, GAP 15.

## Must respect the PM answers

- Send within a minute, not inside the save (GAP 1).
- Only status and notes are sent (GAP 3).
- Non-admin saves stay local (GAP 9).
- First send never overwrites CRM (GAP 11).

## Current state the skill should trace (added for run-2)

| ID | Branch | Flow |
| --- | --- | --- |
| C1 | app | `OrdersController::update` loads, fills and saves an order |
| C2 | app | `OrdersController::destroy` deletes an order |
| C3 | CRM side or Between | `CrmPull::run` writes orders from records with updateOrCreate |
| C4 | Between, sending to CRM | NONE. Nothing sends to CRM today |

PM QUESTION expected from current state: the pull overwrites app edits to status and notes on every run. Should that change?

## Design the skill should reach (added for run-2)

| ID | Expectation |
| --- | --- |
| P1 | An ARCH for sending changes to CRM cites the precedent `src/Jobs/DeliverWebhooks.php` and the standard `.claude/rules/jobs.md`, with USE mirror. A new, different queue design is a miss. |
| P2 | The send job sets the tenant first, per the standard. This covers H3. |
| P3 | `src/Console/ImportCsv.php` appears only as NOTICED or a hazard. Any DELTA or ENABLE that changes the importer is an error. |
| P4 | No DELTA without a real BECAUSE. `check_edd.py delta` enforces this. |

## Scoring

- Blast radius: found, missed, unsupported, for K1 to K10.
- Hazards: found, missed, for H1 to H6.
- Decisions: each pending GAP listed with owner Product.
- PM answers: count any EDD statement that contradicts an ANSWER line as an error.
