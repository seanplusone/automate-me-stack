# Reference: infrastructure

Load for shell scripts, CI workflows, Dockerfiles, IAM policies and anything that changes cloud resources. If the repo has its own guardrail skill, load it too; its failure classes win over this list.

## Risk classes

**Validation after the first write.** A script that says it aborts "before anything changes" must check every target before its first write. Guards inside the write loop abort halfway and leave a partial state. Look for the check and the write in the same loop body.

**Name-match guards.** A substring or pattern check on a resource name is a guard, not a boundary. Ask what stops the script when the pattern matches the wrong thing, and whether the guard checks the name that is actually unique (the cluster, not the service inside it).

**Credential scope.** Which profile or role runs this? If staging and prod share an account, only IAM separates them. A script that uses the ambient `AWS_PROFILE` runs as whatever the operator exported last. Read the policy that grants the profile before suggesting it as the fix; a staging-only profile often lacks the actions a new script needs.

**Ambient defaults.** Docs or scripts that set a global default (`export AWS_PROFILE=...` in a shell profile, a default kube context) change every other tool that falls back to it. Grep the repo's other scripts for the same variable and check what their guards assume. Before saying the default changes a tool's behaviour, read what that tool does with neither the flag nor the variable set. It may already fall back to the same credentials.

**Partial failure.** With `set -e`, a failed call stops the run midway. Is a rerun safe? Calls that set a desired state (desired count, start or stop) are idempotent; calls that add or create are not.

**Order of operations.** Bring dependencies up before the things that use them, and take them down after.

**Hard-coded identifiers.** Instance IDs, generated resource names and account numbers go stale when the resource is replaced. Prefer a lookup by tag, or say in the comment that the list must be maintained.

## Measuring

Do not run anything against real cloud accounts. Put a stub of the CLI first on `PATH` that appends each call to a log and returns canned output for the read calls the script makes. Run the script, then read the log. To test a guard, make the stub return a value the guard should refuse, and count the writes that happen before the abort.

```bash
mkdir -p stub/bin
cat > stub/bin/aws <<'EOF'
#!/usr/bin/env bash
echo "AWS $*" >> "$LOG"
# canned output for read calls goes here
EOF
chmod +x stub/bin/aws
LOG=$PWD/calls.log PATH=$PWD/stub/bin:$PATH bash <script under test> <args>
```

A dry-run flag proves only what the script prints. The stub proves what it calls.
