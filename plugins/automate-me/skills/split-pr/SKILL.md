---
name: split-pr
description: Decide whether a branch or PR is too big to review well, and if it is, which files go in each smaller PR and in what order. Use for "is this PR too big", "should I split this PR", or "where should I cut this branch". Reviewing the code is review-pr; branch names, bases and tickets for a stack come from the repo's own branch skill.
---

# PR split

Two answers: whether the change reviews well as one PR, and if not, the ordered slices it becomes. The output is a plan. Never create a branch, PR or ticket without a separate instruction.

`$SKILL_DIR` is this skill's directory, printed as "Base directory for this skill" when it loads.

## Steps

1. **The range.** For a PR, get the base and head the way `../review-pr/playbooks/review-a-pr.md` step 1 does: fetch both from the matching remote and use the merge base. For a local branch, use the remote's default branch, freshly fetched. A local `master` or `main` is usually behind and inflates the diff.

2. **Measure.** Run `python3 "$SKILL_DIR"/check/size.py <base> <head>` in the repo. Leave out files that will not ship in the PR, such as agent config, planning notes or generated output, with `--exclude <glob>`, and say what you left out. The script owns the thresholds. Quote its numbers; never estimate them.

3. **Verdict.** Start from the script's verdict, then move it for what the numbers cannot see.
   - Toward splitting: two tickets in one change, unrelated features, or a feature mixed with a refactor. Read the ticket keys in the branch, commits and body. A change to a shared base class or trait mixed with features that use it also counts.
   - Toward one PR: generated code, a mechanical rename, or a change that only works if every part lands together.

   Name the reason when you move it. A split only pays when each slice gets a better review than the whole would.

4. **Plan the slices.** Only when the verdict is to split.
   - Find the dependencies before grouping anything. For each class, method, route, table, column or config key the change adds or changes, grep where it is defined and every file that uses it. A slice may use only what the base or an earlier slice defines.
   - Do not split by layer by default. Before separating a schema change from code, check whether the migration names code, such as a model class or a constant. If it does, they ship together.
   - A file every slice edits, such as a test registry, route file or config array, cannot ship in its final form in the first slice. Each slice carries its own version of it, built from the base.
   - Tests ship in the slice whose code they test.
   - Every slice leaves the app working on its own. Core behavior first, extras after. Fewer, larger slices beat many tiny ones. Aim for slices the script calls `review as one`.
   - Stacked-PR mechanics (branch names, bases, tickets per slice) belong to the repo. Follow its branch skill or rules when it has them.

5. **Prove the plan.** Write it as `plan.tsv`, one `<slice>\t<path>` line per file, slices in merge order, in `<scratchpad or $TMPDIR>/split-pr-<name>/`. Run `python3 "$SKILL_DIR"/check/size.py <base> <head> --plan <dir>/plan.tsv`. It fails when a file is in no slice or in two, or when the plan names a file the diff does not have. It also fails when the base changed a sliced file after the head branched. A slice cut from the head's copy would quietly revert that change, so merge the base into the head before slicing. Fix what it flags.

   When the repo has a safe test runner, build the first slice in a throwaway worktree (`git checkout <head> -- <slice 1 files>` on the base) and run it. A fatal names a file that belongs in that slice.

## Reply

At most 8 lines, then the table when splitting. Write it to W17 to W19 in `../shared/writing-rules.md`: who it affects first, every claim labeled measured, inferred or a guess, and nothing on this list dropped.

1. The verdict and the script's numbers in one line.
2. The reason, if you moved the verdict.
3. What you excluded from the count.

When splitting, add one row per slice: order, title, files, lines added, what it depends on, and what it proves on its own. Give the path to `plan.tsv` and the last line of the plan check.
