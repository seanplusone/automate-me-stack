# PRD: Send Ticket Changes Back to the CRM

Author: Product Manager
Status: Draft, not yet reviewed by engineering

## Background

Today, tickets created in the CRM show up in our app. We already pull them in. Customers have asked for the reverse. When they update a ticket in our app, the CRM should show the change too. Right now they have to update both places by hand, and the two often disagree.

## Goal

Customers update a ticket in our app and the change shows up in the CRM, so both always match.

## Requirements

1. When a user saves a ticket in the app, the change is sent to the CRM right away.
2. Users should see the change in the CRM in real time.
3. If someone edits a ticket in the CRM, the app keeps showing the newest version. The existing pull should already handle this.
4. A user can delete a ticket in the app, and it is removed from the CRM.
5. Only admins can send changes to the CRM.
6. A customer can have several thousand tickets. The first time we turn this on, we send all of them.
7. If something goes wrong, show an error message to the user.
8. Reports in the app should always match the CRM.

## Out of scope

- Photos and attachments
- The mobile app

## Things I am not sure about

- I think the CRM will tell us whether an update worked, but I have not confirmed it.
- I do not know what happens if two people edit the same ticket.
- Is our current pull instant or on a schedule? I assumed instant.
- Launch target is the end of next month, for our first three customers.
