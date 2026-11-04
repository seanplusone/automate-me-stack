# Voice: engineers

Read before drafting any review comment for an engineer. The comments below show the voice the user posts by hand, on an invented orders service. Match them. For anything a PM reads, use `pm.md` instead.

- "The webhook secret is compared with `==`, so the check can leak timing. Can it use `hash_equals` here and in `RefundWebhookController`?"
- "No job in `config/schedule.php` calls `PruneExpiredCarts` yet. Is it meant to be scheduled in this PR, or in a later one?"
- "The workers run on PHP 8.3 and CI only runs 8.1. Could the test matrix add 8.3?"
- "`PAYMENT_API_KEY` is passed as a command-line argument, so it shows in the process list. Could it come from the environment instead?"
- "The comment says \"never retried\", and `$tries` is 3 two lines below. Which one is right?"
- "The changelog link points at the 2.4 release notes, not the issue."

## The shape

1. A fact about the code, stated plainly. It names the file, value or behaviour.
2. The ask, as a direct question, with the fix in it when the fix is known.

## Three habits that make a comment read oddly

**Starting with "This".** "This retries forever when the gateway times out..." makes the reader work out what "this" is. Name the thing first: "Every worker connects with the same `DB_USERNAME`...", "`retryPayment` only checks...", "The migration guide says...".

**Stating a guess as a fact.** If you did not check it, it is the question. "This index locks the orders table for the whole deploy" assumed the table is large. "How many rows does `orders` have in production? Past a few million, the index build blocks writes for minutes" asks it.

**Tacking a reason onto the ask.** "...might help, given checkout calls it on every page load?" argues instead of asking. Put the fact in the first sentence and keep the ask short: "Would a cache on `TaxRate::forRegion` be worth it?"

## Two ways to get it wrong

**Too stiff.** Process words and compressed phrasing. "Fix conflict and refresh docs?", "README partly outdated", "Two blocking items and one nit below", "LGTM pending the above".

**Too eager.** Pleasantries and softeners added to sound friendly. "Love the test coverage here! One small thought...", "Totally optional, ignore if you like", "Out of curiosity", "Quick flag", "Really appreciate you picking this up, the support team will be thrilled". The user's comments have none of these. Being direct and specific is the respectful part.

## The same comment, three ways

From an invented review of a PR that adds a bulk refund command.

| | Comment |
|---|---|
| Too stiff | The docblock says an invalid order ID aborts before any refund, but the ID check runs inside the loop. With a fake gateway, `refund:bulk` issued 4 refunds before exiting 1. Should the command validate every ID first? |
| Too eager | Love how readable the command is! A small thought, and feel free to push back: since the ID check happens inside the loop, a typo in the list might leave some refunds done and others not. Maybe validate the list before starting? |
| Right | The order ID check runs inside the loop, so a bad ID stops the run after some customers are already refunded. Could the command validate the whole list before it refunds anything? |

| | Review body |
|---|---|
| Too stiff | LGTM pending the above. Conflict in `config/payments.php` to resolve first. Two blocking items and one nit below. |
| Too eager | Really appreciate you picking this up, the command is clear and well tested! Happy to approve. There's a small conflict with main to sort out first, and I left a few thoughts below. |
| Right, no comments | (empty) |
| Right, with comments | Approving. The `--actor` option can wait for a later PR. |

## More example comments

All from the same invented review.

- "Every run of `refund:bulk` logs as the `system` user, so the audit log can't tell who started it. Could the command take an `--actor` option?"
- "`RefundServiceTest` builds the gateway client with the live key. Is a test meant to reach the real gateway? If not, the fake client in `tests/Fakes` might be the better fit."
- "`isRefundable` only checks the order status, not whether a refund already exists. Lines 40 and 52 also still say the limit is 100 orders, but `MAX_BATCH` is 250 now."
- "`config/payments.php` conflicts with main, where the payment settings moved into `config/refunds.php` last week. The comment listing unused config keys also mentions `refunds.mode`, which this PR starts using."
- "The README says refunds are always queued, but step 3 of the command sends them inline when the batch has fewer than 10 orders. Should the README mention the inline path?"

Two drafts of the audit log comment show the habits above. Rejected: "This always writes `system` to the audit log, which means we lose track of who refunded what. Is an `--actor` option worth adding, since finance reviews that log?" Kept: the first bullet.

A review body is empty for a clean approval. An approval with comments says so in one sentence, naming what can wait. Add one more sentence only for something with no line to sit on, such as "The PR title still says 50 orders per batch."
