# Key: crm-sync-sample

The known gaps in `input/prd.md`, planted by hand. Never show this file to the skill.

## How to score

- Run `python3 check/score_case.py cases/crm-sync-sample/key.md <gaps.txt>`. A gap is **found** when a GAP line sits on the row's point, or quotes its evidence, and its question names every term in the row's `Terms:` line. A person still checks that it asks the same question. Wording can differ.
- If the owner differs from the one below, the script notes it. It does not count as a miss.
- Gaps in the output with no PRD quote behind them are **unsupported** and count as errors. `check.py gaps` finds them.

## Expected operation tags

- R1 reads as `update`. The Background says "When they update a ticket in our app".
- R3 is `read`.
- R4 is `delete`.
- Expected missing operation: `create`. The PRD never says a new ticket made in the app is sent to the CRM.

## Gaps the skill should find

| ID | Point | Question | Owner | PRD evidence |
|----|-------|----------|-------|--------------|
| G01 | R1, R2 | "Right away" and "real time" are not defined. Are they the same thing? | Unclear wording | "sent to the CRM right away", "in real time" |
| G02 | R1 | What is "the change"? All fields or only edited ones? | Unclear wording | "the change is sent to the CRM" |
| G03 | R1 | Can a ticket created in the app be sent to the CRM? | PM | not stated |
| G04 | R3 | How is "newest version" decided? | Unclear wording | "keeps showing the newest version" |
| G05 | R3 | Does the existing pull run instantly or on a schedule? | Engineer | "Is our current pull instant or on a schedule? I assumed instant." |
| G06 | R3 | What happens if the pull fails or runs late? | Engineer | not stated |
| G07 | R4 | Is the record deleted for good in the CRM, or marked? Is it kept in the app? | PM | "it is removed from the CRM" |
| G08 | R4 | What if the CRM delete fails, or the record is not in the CRM? | Engineer | not stated |
| G09 | R5 | Which users are admins? | PM | "Only admins can send changes to the CRM." |
| G10 | R5 | What happens when a non-admin saves? | PM | not stated |
| G11 | R5 | What does a non-admin see? | PM | not stated |
| G12 | R6 | Who turns the feature on, and is it per customer? | PM | "The first time we turn this on" |
| G13 | R6 | How many records per request, and is there a limit? | Engineer | "several thousand tickets" |
| G14 | R6 | What if some tickets already exist in the CRM? | PM | not stated |
| G15 | R6 | What if the first send stops halfway? Can it resume? | Engineer | not stated |
| G16 | R7 | Who sees the error, and what does it say? | PM | "show an error message to the user" |
| G17 | R7 | What happens to the unsent change after the error? | PM | not stated |
| G18 | R8 | Which reports? | Unclear wording | "Reports in the app" |
| G19 | R8 | "Always match" cannot hold during delay or failure. How much lag is acceptable? | Unclear wording | "should always match the CRM" |
| G20 | PM unsure | Does the CRM confirm that an update worked? Unverified outside fact. | Engineer | "I think the CRM will tell us whether an update worked, but I have not confirmed it." |
| G21 | PM unsure | What happens if two people edit the same ticket? | PM | "I do not know what happens if two people edit the same ticket." |

Terms: G01 | right away/real time
Terms: G02 | field
Terms: G03 | create
Terms: G04 | newest
Terms: G05 | schedule
Terms: G06 | fail/runs late/delay
Terms: G07 | permanent/for good/marked
Terms: G08 | fail/not in the crm
Terms: G09 | which users/who counts/role
Terms: G10 | non-admin
Terms: G11 | non-admin | see/shown/message
Terms: G12 | who starts/who turns/per customer
Terms: G13 | batch/per request/limit
Terms: G14 | already exist/overwrite/differ
Terms: G15 | resume/halfway
Terms: G16 | who sees/what does it say/what it says
Terms: G17 | retry/unsent/lost
Terms: G18 | which reports
Terms: G19 | delay/lag/every moment
Terms: G20 | confirm/success/worked
Terms: G21 | two people/same ticket

## Not expected from this skill

The skill checks each point alone. These need two points at once, so finding them is a bonus and missing them is not a miss.

- X1. R1 says "a user saves" but R5 says only admins send.
- X2. R1 sends to the CRM and R3 pulls back from the CRM. The two could trigger each other in a loop.
- X3. R2 and R8 promise real time and "always match", but R7 admits failures can happen.
