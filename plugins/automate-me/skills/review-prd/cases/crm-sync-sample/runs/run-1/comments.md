DRAFT. Not sent. A person reviews and submits.

## C1 (GAP 1, R1, Unclear wording)
Quote: "the change is sent to the CRM right away."
Missing: "Right away" has two readings: sent inside the save action, or queued and sent soon after.
Why it matters: The two readings change what the user waits for on save.
Proposed default: Do send the change in the background right after save, within 60 seconds. If it is not sent in 60 seconds, do show the sync as pending.

## C2 (GAP 3, R1, PM)
Quote: "not stated"
Missing: The PRD does not say which ticket fields are sent to the CRM.
Why it matters: Sending the wrong fields can overwrite data that CRM owns.
Proposed default: Do send only fields that users can edit in the app. If a field is created in CRM only, do not send it.

## C3 (GAP 4, R2, Unclear wording)
Quote: "Users should see the change in the CRM in real time."
Missing: "Real time" could mean the data reaches the CRM at once, or CRM users see it update live without a refresh.
Why it matters: A live CRM screen refresh is a different feature from sending data.
Proposed default: Do treat it as the same as R1 and make no promise about live refresh. If live refresh is wanted, do add it as its own requirement.

## C4 (GAP 5, R3, Unclear wording)
Quote: "the app keeps showing the newest version."
Missing: "Newest" is not defined. It could mean the CRM edit always wins, or the latest timestamp wins.
Why it matters: Without a rule, an old CRM edit could overwrite a newer app edit, or the reverse.
Proposed default: Do show the version with the latest edit time. If both edit times are equal, do show the CRM version.

## C5 (GAP 8, R4, PM)
Quote: "A user can delete a ticket in the app, and it is removed from the CRM."
Missing: The PRD does not say whether a delete is permanent or can be recovered, or who may delete.
Why it matters: A permanent delete in the CRM cannot be undone if the user made a mistake.
Proposed default: Do ask the user to confirm before a delete is sent. If the user is not an admin, do not allow the delete.

## C6 (GAP 9, R5, Unclear wording)
Quote: "Only admins can send changes to the CRM."
Missing: It could mean non-admin saves stay in the app only, non-admins cannot save at all, or an admin must trigger each send.
Why it matters: Each reading leaves the app and the CRM out of step in a different way.
Proposed default: Do send changes saved by admins and keep non-admin saves in the app only, marked as not sent. If non-admin saves must reach the CRM, do let an admin approve them.

## C7 (GAP 11, R6, PM)
Quote: "The first time we turn this on, we send all of them."
Missing: The PRD does not say who starts the first send or whether it overwrites CRM values that differ.
Why it matters: A blind overwrite of several thousand tickets could replace correct CRM data.
Proposed default: Do let an admin start the first send per customer. If a value differs in the CRM, do not overwrite it and list it for the admin.

## C8 (GAP 12, R7, PM)
Quote: "If something goes wrong, show an error message to the user."
Missing: The PRD does not say which failures show a message, what it says, who sees it, or whether the user can retry.
Why it matters: A vague error leaves the user unsure whether their change reached the CRM.
Proposed default: Do show the message to the user who saved, with a retry button. If the retry fails twice, do show the message to an admin as well.

## C9 (GAP 13, R8, Unclear wording)
Quote: "Reports in the app should always match the CRM."
Missing: "Always" could mean a match after a short delay, or a match at every moment including during failures.
Why it matters: A match at every moment cannot be promised while a send is pending or has failed.
Proposed default: Do promise a match once all sends are done. If a send is pending or failed, do mark the affected ticket in the report.

## C10 (GAP 15, U2, PM)
Quote: "I do not know what happens if two people edit the same ticket."
Missing: The PRD does not say which edit wins when two people edit one ticket.
Why it matters: A silent overwrite loses one person's work.
Proposed default: Do let the last save win and show a notice to the earlier editor. If the earlier editor's save is still open, do ask them to reload before saving.

## For the design doc
- GAP 2, R1: What happens to a change if the CRM is unreachable or rejects it: retry, queue, or drop?
- GAP 6, R3: Does the existing pull read back changes the app just sent, and could it overwrite or loop?
- GAP 7, U3: Is the current pull instant or on a schedule? Unverified.
- GAP 10, R6: How is the first load of several thousand tickets batched, throttled and resumed? The CRM limits are unverified.
- GAP 14, U1: Does the CRM report success or failure of an update? Unverified.
