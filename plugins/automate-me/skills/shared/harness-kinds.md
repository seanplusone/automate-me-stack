# Harness kinds

The thing that proves a fix option worked. It fails on today's code and passes after the change. Use these names on the page.

| Kind | What it is |
|---|---|
| `tests/safe test` | A write-safe test in the repo's safe suite. It fails before the change and passes after. |
| `unit test` | A test in the target repo, outside a safe suite. It fails before the change and passes after. |
| `findings file` | For an item that answers a question rather than changing code. A file answers it, with each claim labeled and its run or file:line. A fresh agent rechecks two claims. |
| `script check` | A script that exits 1 while the output is wrong and 0 once it is right, such as a lint or a shape check. |
| `revert check` | Restore the changed files from the commit before, rerun, and confirm the test fails again. Pairs with a test, never alone. |
| `route test` | Asserts route order, or that an endpoint refuses a user without the right role. |
| `migration rerun` | Run the migration twice on a database copy, then once with a planted bad row. |
| `prod count (read-only)` | One SELECT on production through `query-db`. It sizes a risk; it proves no fix. |
| `real vendor run` | The change exercised against the real outside service in a test account, with test items deleted after. |
| `browser check` | `verify-web` on the local site, with screenshots of what the user sees. |
| `doc check` | A script or grep over the doc that fails while the wrong sentence is still there. |
| `PM sign-off` | The PM answers a written question. Nothing an agent can prove. |
| `independent verifier` | A fresh agent that never saw the work reruns the harness and reads the diff. Every option's steps end with it. |
