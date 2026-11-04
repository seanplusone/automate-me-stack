# PRD review: Send Ticket Changes Back to the CRM

**What I found.** The PRD never says whether a new ticket made in the app reaches the CRM. It does not say who wins when two people edit the same ticket. Several words have two readings, such as "right away", "newest" and "always match". The send to the CRM and the existing pull could trigger each other in a loop.

**Questions for the PM.**
- C1. Does "right away" mean during the save, or soon after?
- C2. Which ticket fields go to the CRM?
- C3. Does "real time" mean the data arrives, or the CRM screen refreshes live?
- C4. How does the app decide which version is newest?
- C5. Is a delete in the CRM permanent? This comment failed evaluation.
- C6. What does "only admins can send" mean for other users?
- C7. Who starts the first send, and does it overwrite CRM values?
- C8. Which errors show a message, and who sees it?
- C9. Does "always match" allow a short delay?
- C10. Which edit wins when two people edit one ticket? This comment failed evaluation.

**For the design doc.**
- GAP 2. What the app does when the CRM is down or rejects a change.
- GAP 6. Whether the pull reads back the app's own changes and loops.
- GAP 7. Whether the pull is instant or scheduled.
- GAP 10. How the first send of several thousand tickets is split up and resumed.
- GAP 14. Whether the CRM reports success or failure of an update.

**Not verified.** The CRM batch limits and whether the CRM confirms an update. The PM has not confirmed either, and this review read no CRM docs.

**Stopped or blocked.** The evaluator failed C5 and C10. C5 adds a delete permission the PRD never raised. C10 uses a condition that is not defined. A person must fix both before sending.

**Changed.** Nothing. The comments are a draft at runs/run-1/comments.md.

Counts: points 8, scenarios 1, gaps 15 (PM 5, Engineer 5, Unclear 5), comments 10, failed evaluation 2.
