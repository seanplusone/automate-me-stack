# Reference: docs

Load when the diff is Markdown: runbooks, ADRs, design docs, READMEs. A document is reviewed for whether it is true and whether it does its job, not for style.

## Questions to answer

**Does it close the ticket it opens with?** Read the problem statement, then the scope. When the motivating problem is not covered by the scope, that is the finding.

**Is each claim about the system true?** "All 8 hosts are registered", "port 22 is closed", "nothing automated depends on it". Check each against the code, the config or a companion PR. A claim you cannot check without live access becomes a question, not a statement.

**Does it agree with its companion documents?** A runbook and its ADR, a design doc and its epic. Compare their commit times. The one written first is usually the stale one. Check both directions: a doc can be ahead of the code (describes something not built yet) or behind it.

**Does following it go wrong?** Run the instructions in your head against the repo's other tools. A setup step that sets a global default, a command that collides with a local service, a credential retrieval that depends on something the same doc plans to remove.

**Is the index right?** ADR numbers, index entries and "reserved" notes go stale when a sibling merges first. Check `mergeable` on the PR.

**Was it rewritten or edited?** Compare the doc against its earlier commits. A rewrite can silently drop a section a reviewer already approved.

**Does each number measure the risk it is cited for?** A production count or a latency is evidence only for the question it answers. Read the query behind it.

**Is there a competing explanation?** For a doc that diagnoses a problem, search the tracker by symptom before accepting its cause.

Quote the sentence a finding disputes, so the author does not have to hunt for it.

## Leave alone

A gap the author has named ("not measured yet", "tracked separately", "out of scope") is the document doing its job. Do not raise it. A gap that is unnamed, or named in one section and contradicted in another, is reviewable.

Do not propose a redesign. Name what does not hold and let the author choose.
