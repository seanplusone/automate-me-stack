# Reference: bundles

Load when `classify.py` labels any changed file `generated`. The PR commits another repo's build output. Review the source PR's code with `frontend.md`, and review the link between the two PRs here. Do not review the built files, and never anchor a comment on one (`check_drafts.py` fails it).

Ask, for each bundle PR:

1. **Source.** Which PR and commit was it built from? Has that PR merged? If not, say in the review body that this PR merges after the source PR, and judge the bundle on whether it matches the source. If the source head moved past the built commit, does `git diff <built>..<head> -- apps/<app>` show changes?
2. **Same bytes.** Rebuild the source at the built commit. Does `cmp` find it equal to the PR head? If the install fails, say the rebuild was not run, and fall back to grepping for strings the source PR adds.
3. **Leftovers.** Does the folder still hold an older `index-<hash>` file next to the new one? The loader can serve the old build.
4. **Overlap.** Does another open PR change the same folder? Which must merge first, and which must be rebuilt?
5. **Host.** Is the copy served anywhere besides the main app, such as a second service or a legacy host? If so, does that host give the bundle the same origin, session and injected values, and is every copy built from the same commit?
6. **Paths and baked values.** Does the built output hold any root-relative `"/assets/` URL, `localhost` or stage host, or secret?
