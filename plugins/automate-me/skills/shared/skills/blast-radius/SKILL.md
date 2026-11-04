---
name: blast-radius
description: List everything that fires, filters or depends on an entity a change will touch, with file and line for each. Use before designing, fixing or reviewing a change that writes that entity.
---

# Blast radius

Input is one entity a change writes, such as a model, table or class, and the repo. Output is a fixed-format list a script can check. Do not judge or design. Only find and cite.

This follows the same idea as a "map the blast radius before you write" gate: state in, state out, siblings. This skill makes it checkable.

## Step 0. Load the project reference

Read `.claude/blast-radius.md` in the project repo if it exists. It says where this framework hides hooks and scopes. If it does not exist, write `REFERENCE: none`, continue with the generic steps, and tell the person to create one from `blast-radius-reference.md` in this folder.

Then list the search roots. Include:

- The main repo, including any in-repo packages directory.
- `vendor/`, if it is checked out.
- Any other repo or app that reads or writes the same database tables.

Write them as `ROOTS: <path>, <path>`. Every later search runs over all roots.

Why. Frameworks hide side effects in different places. A plain search for "boot" misses a fork that boots traits under another name. A second app writing the same table is a writer too, even though it lives in another repo.

## Step 1. Find the entity

Find the class and its file. Walk up every parent class and every trait it uses. List each one.

Check. Every parent and trait has a file path that exists.

## Step 2. Hooks

List what runs when the entity is created, saved, updated or deleted: model events, observers, listeners, trait boot methods. For each, say what it does in one line.

Check. Each "what it does" comes from reading the body of the code, not from the hook's name. If a hook triggers other hooks, say whether it really does. A bulk query delete, for example, skips the child model's own hooks.

Why. A real file and line with a wrong description passes the script check, and whatever is built on it inherits the wrong meaning.

## Step 3. Scopes

List everything that changes what a query for this entity returns: global scopes, scopes added at query time, scopes that depend on the logged-in user or the tenant.

Why. A background job may run without a user or tenant, so a scope can hide rows or match the wrong one.

## Step 4. Writers and readers

- Writers: every place that creates, updates or deletes the entity.
- Readers: every place that reads the fields the change will touch.

Search by the class name and by each field name. Record the search you ran.

## Step 5. Mark what you could not find

If a search returns nothing, write `NOT FOUND` with the exact search. It means not found in the listed roots, nothing more. Never fill a gap with a guess.

## Step 6. Verify with a different model

Run this after the script check passes. A different model reads the code behind every BR line and writes one line for each description that is wrong:

```
WRONG BR | <id> | <what the code really does>
```

Fix every WRONG BR before anyone builds on the list. If only one model family is available, follow `../panel-check/SKILL.md` step 1.

## Output format

Use this format exactly. Every quote must be the real code on that line.

```
ROOTS: <path>, <path>
ENTITY: <class> | <file>
CHAIN: <parent or trait> | <file>
HOOK BR<n>: <event> | <file>:<line> | "<code on that line>" | <what it does>
SCOPE BR<n>: <name> | <file>:<line> | "<code on that line>" | <what it filters>
WRITER BR<n>: <file>:<line> | "<code on that line>" | <what it writes>
READER BR<n>: <file>:<line> | "<code on that line>" | <what it reads>
NOT FOUND: <what> | <search command>
SEARCHES: <every search command run, one per line>
COUNTS: hooks <n>, scopes <n>, writers <n>, readers <n>, not found <n>
```

## Hard requirements

- The run fails if any `file:line` does not exist, or the quote is not on that line. Check it with `python3 "$SKILL_DIR"/../../check_blast.py <roots> <file>`. `$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.
- BR numbers are unique. Callers cite them.
- Read only. Never run the app, its tests or its commands.
