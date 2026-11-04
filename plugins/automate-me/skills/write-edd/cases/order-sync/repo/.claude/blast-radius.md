# Blast radius reference

## Search roots

- This repo.

## Where hooks live

- Model events are registered in each model's static boot().
- Traits boot through a method named __boot_<TraitName>, called from Framework/Model::boot. A search for "boot" in a trait finds them.

## Where scopes live

- Global scopes are added with addGlobalScope inside trait boot methods.

## Standards

- .claude/rules/jobs.md

## Capability index

- None recorded yet.

## Jargon for PM questions

- outbox
- payload
- tenant

## Known traps

- None recorded yet.

## Docs known to be wrong

- None recorded yet.
