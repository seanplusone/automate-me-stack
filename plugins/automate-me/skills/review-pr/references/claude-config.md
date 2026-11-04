# Reference: Claude Code config

Load when the diff touches `.claude/` (rules, skills, commands, settings), a `CLAUDE.md`, or a Claude Code plugin or marketplace. These files are code that other agents run. Review what an agent does when it follows them, not how they read.

## Risk classes

**Paths that do not resolve.** Resolve every path a skill or command names from where it actually runs. That is the session's working directory, usually a repo root, not the skill's own folder. Plugin-internal files need `${CLAUDE_PLUGIN_ROOT}`. A path the agent writes to matters most, because a wrong one creates a stray folder instead of failing. A local checkout's folder name can differ from the repo's name, and a machine can hold more than one clone of a repo. A path that names a repo folder misses the checkout the skill runs in, or lands in another clone. Paths into the repo a skill runs in stay repo-relative.

**Moved files.** When skills move between repos or into a plugin, diff each old file against its new copy. Rewritten paths, renamed cross-references (`/name` to `/plugin:name`) and dropped lines are where the bugs are. Then run `check/moved_drift.py` against the source repo's default branch. It catches edits that landed on the source after the copy, which the move PR's companion then deletes.

**Stale references.** Grep the repo for every removed skill or command name and old path (`/name`, `.claude/skills/name`) in `CLAUDE.md`, rules, docs, tests and scripts. Then the other direction: every skill or command a moved or new file tells the agent to use must exist in the plugin or the repo. A name that resolves only on the author's machine is a personal skill, and the step is broken for everyone else.

**Plugin wiring.** An `enabledPlugins` key is `<plugin>@<marketplace>`. Check both names against the marketplace's `marketplace.json` and the plugin's `plugin.json`. Say what a teammate who never installed the marketplace sees. Without `extraKnownMarketplaces` in the committed settings, they get no prompt to install it.

**Merge order.** A PR that removes skills and one that adds them elsewhere must merge in order. Say what each user has if only one merges.

**Settings that grant power.** A change to `permissions`, `hooks` or sandbox settings in a committed `settings.json` applies to every agent in the repo. Review it as a security change. Name what it lets an agent run without asking.

**Trigger overlap.** A new or changed skill `description` that matches the same requests as an installed skill makes the choice between them random. Name the other skill. A skill that starts loading in more projects, such as one moved into a plugin several repos enable, can overlap in each of them. Compare its description against the skills enabled there.

**A new rule against old text.** The PR adds a rule to a skill, such as never, always or stop. Grep the rest of that skill and every file it sends the agent to for steps that break the rule. Old sections carried over by the move are where they hide.

**Rules are claims.** Every later agent loads `.claude/rules/` through its `paths:` globs, so a false statement spreads to all of them. Check each claim against the code, and check that each glob matches real files. The same holds for a plugin's `references/` and checklists that skills load. Check their versions, pins and counts against the source.

**Commands in a skill.** Run each command a skill gives, against a safe target, or say which ones were not run.
