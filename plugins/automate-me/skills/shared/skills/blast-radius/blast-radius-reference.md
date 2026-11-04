# Blast radius reference (template)

Copy this to `.claude/blast-radius.md` in the project repo and fill it in. Keep it about where to look, not about any one feature. The blast-radius skill reads it first. A section another skill reads says so under its heading.

## Search roots

Also read by the current-state skill.

- <main repo path, including in-repo packages>
- <vendor path, if checked out>
- <other apps that read or write the same database tables>

## Where hooks live

- <how model events are registered>
- <how traits boot, if the framework renames the boot method>
- <observers or listeners, and where they are registered>

## Where scopes live

- <global scopes and how they are added>
- <scopes that depend on the logged-in user or tenant>

## Standards

Read by the design-options skill, step 2.

- <rules files the design must follow, one per line>

## Capability index

Read by the design-options skill, step 3.

- <capability> -> <where it already lives>, for example `access tokens per customer -> app/Services/OAuth/`

## Jargon for PM questions

One internal term per line. A skill that writes questions for a PM copies this list into a plain text file and fails a question that uses one.

- <term>

## Known traps

- <a framework behavior that silently differs from the docs, with file:line>

## Docs known to be wrong

- <doc path>: <what it gets wrong>
