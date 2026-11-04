# Writing rules

Load this before writing any prose a person reads: questions for the PM, PR comments, chat replies and reports. It does not apply to the PRD, which is never changed, or to fixed-format lines meant for the script.

Adapted from pstack's `unslop` skill, with its rule number in brackets, and from the "Writing the reply" section of pstack's `poteto-mode` (W17 to W19). Our ids are stable. A removed rule leaves a gap.

`[script]` means `shared/check_writing.py` catches it. `[judgment]` means a person or a second model checks it.

## Punctuation

**W1. No long dashes.** [script] (unslop 13)
- Bad: "The pull runs on a schedule — not instantly."
- Good: "The pull runs on a schedule. It is not instant."

**W2. No colon joining two halves of a sentence.** [script in review-pr comments, judgment elsewhere] (unslop 14)
A colon before a list is fine.
- Bad: "The risk is simple: old data wins."
- Good: "Old data can overwrite new data."

**W3. Straight quotes only.** [script] (unslop 19)

## Words

**W4. No chatbot phrases.** [script] (unslop 20, 22)
`Great question`, `I hope this helps`, `Let me know if`, `Certainly`. Delete them.

**W5. Plain words.** [script] (unslop 7, 31, plus `robust`, `seamless` and `ensure`, which are ours)
`utilize`, `leverage`, `facilitate`, `crucial`, `pivotal`, `robust`, `seamless`, `delve`, `enhance`, `ensure`, `additionally`, `garner`, `interplay`, `intricate`, `showcase`, `testament`, `tapestry`, `vibrant`, `fostering`. Use the plain word: use, help, important, works, check, also, get, shows.

**W6. No filler.** [script] (unslop 23)
- `In order to` becomes "To".
- `Due to the fact that` becomes "Because".
- Delete `It is important to note that`.

**W7. Hedge once, or not at all.** [judgment] (unslop 24)
- Bad: "This could potentially cause a possible conflict."
- Good: "This may cause a conflict."

**W20. Say "is".** [script] (unslop 8)
`serves as`, `stands as` and `boasts` become "is" or "has".

**W21. No `not just X, but Y`.** [script] (unslop 9)
- Bad: "This is not just a rename but a behavior change."
- Good: "This changes behavior."

**W22. Concrete nouns.** [script, for the listed words] (unslop 26)
`substrate`, `locus`, `vantage`, `nexus`, `bedrock`, `paradigm`, `modality`, `north star`, `flywheel`, `endgame`. Use the plain noun. Wedge, surface, harness and ratchet are a judgment call, because code uses them literally.

**W23. Cut the adverb.** [judgment] (unslop 30)
- Bad: "This significantly slows the page."
- Good: "This adds 2 seconds to the page."

## Sentences

**W8. Say what happens, not how it feels.** [judgment] (unslop 27)
If a sentence cannot become a fact, a number or an instruction, cut it.
- Bad: "This keeps the sync smooth and reliable."
- Good: "A failed send retries 3 times, then shows an error to the user who saved."

**W9. One idea per sentence.** [script, over 30 words] (unslop 28)
- Bad: "If an admin saves a record while the pull is running and the other system has a newer edit, the app may keep the older version, which then gets sent back."
- Good: "An admin saves while the pull is running. The other system has a newer edit. The app may keep the older version and send it back."

**W10. Name who does it.** [judgment] (unslop 29)
- Bad: "Changes are sent to the other system."
- Good: "The app sends changes to the other system."

**W11. Whole sentences in prose.** [script, arrows] (unslop 33)
No arrows or symbol-speak in anything a person reads: PR comments, questions for the PM, chat replies and reports.
- Bad: "Save → send fails → retry."
- Good: "If the send fails, the app retries."

Keep the articles and verbs too. "Parser rejects bad date, no write" becomes "The parser rejects a bad date and writes nothing."

A word cap is met by cutting a clause, never the articles.
- Bad: "Main added 50 old-name lines to 14 of them." (written to fit a 50-word comment)
- Good: "Main also added 50 lines that use the old skill names."

**W24. Literal, not figurative.** [judgment] (unslop 32)
No aphorisms, personified code or figurative verbs.
- Bad: "The guard rides along with every save."
- Good: "The guard runs on every save."

## Explaining

For chat replies and reports. PR comments keep the shape in `voices/engineer.md`, and PM questions keep W13 to W16.

**W17. Impact first.** [judgment]
Open with who notices the change and what changes for them: the PR author, the PM, or the next engineer who owns the code. Mechanics come after.
- Bad: "Added a size step to step 1 of the playbook."
- Good: "A review of an oversized PR now says so in the chat reply. The check runs in step 1."

**W18. Label every claim.** [judgment]
Each claim carries its evidence or its label in the same sentence: measured, and with what; inferred, and from what; or a guess. Never hand the reader a check you could have run.
- Bad: "The size limit is too strict."
- Good: "On the last 60 merged PRs, the size limit said to split 11 of them."

**W19. Short, but nothing dropped.** [judgment]
Short sentences do not excuse a missing part. Everything the reply format names stays, including what was not verified, the tradeoffs and the open decisions.

**W25. Simple first, detail folded.** [judgment]
On a page that lists findings, comments or claims for review, each item opens with one plain sentence of at most 20 words: what goes wrong and for whom. Under it go the verdict and a fix of at most 12 words. The full story, the quoted source and the evidence sit in closed sections below. A reader skims the plain lines to see the whole set, then opens only the items they need to verify.
- Bad: a card that opens with "The cache key hashes every column (design doc line 212), and spike 3 says `updated_at` and `last_seen_at` are columns".
- Good: "Columns that change on their own, like 'last seen', make every cached page look stale." Then "Is it right? Yes. Fix: leave self-changing columns out of the key." Then the folded story and evidence.

## Our own rules

**W12. Feedback, not answers.** [script, in review-prd's open-questions check]
A question for a PM carries no proposed answer and no engineering argument. The engineer says what is unclear. The PM decides.

## Questions for a PM

These apply to every numbered question in a PM question list. `review-prd/check/check.py pm-list` checks the `[script]` ones.

**W13. One situation per question.** [script, at most three question marks] [judgment, every ask is about the same situation]
Write it the way an engineer would raise it with a PM across a table. Related asks about one situation stay together, up to three. Questions about the same situation from different angles become one.
- Bad, split apart: "How long should we keep the history?" Then, as another question: "Who should see the history?"
- Good: "The app keeps a record of every invoice it sends. How long should it keep that record? Should anyone besides admins see it?"
- Bad, two situations in one: "If a send fails, who is told, and should admins be able to undo a bad import?"

**W14. Plain words.** [script, project jargon list]
No internal system terms. The project keeps a jargon list, one word per line, and the script flags those words.
- Bad: "Do line items sync, or only the order header?"
- Good: "If someone removes an item from an order in the app, should it disappear from the order in the other system too?"

**W15. Not leading.** [judgment]
Do not assume the answer.
- Bad: "Are private records attached to a site?"
- Good: "What, if anything, is a private record tied to?"

**W16. Purpose first.** [script]
If the purpose question from `review-prd/rules/prd-basics.json` is asked, it comes first among the questions, word for word. It is not asked when the PRD states the customer problem.

## How a rule gets added

Through `shared/playbooks/learn-from-run.md`. A person approves every new rule. If code can catch it, it goes into a check and is marked `[script]`.
