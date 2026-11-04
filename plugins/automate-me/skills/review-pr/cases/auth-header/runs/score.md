# Score: auth-header

A synthetic case: the repos, PRs, code and drafts were written by hand to show how a case is scored. Run 1 is built to fail, so the score table shows what a miss looks like. Run 2 fixes both misses.

| | run-1 | run-2 |
|---|---|---|
| Drafts | hand-written, two linked PRs | run-1 with both misses fixed |
| `score_case.py` | FAIL, 1 of 3 | PASS, 3 of 3 |
| Found by hand | K1 | K1, K2, K3 |
| Unsupported | 0 | 0 |
| Traps hit | 0 | 0 |
| `check_drafts.py` | PASS | PASS |

Both runs pass `check_drafts.py`. The format check and the case score measure different things. A drafts file can be well formed and still miss what the key wants.

## Why run-1 fails

- **K2, site count.** Run 1 commented on the two raw `fetch` calls it happened to read, and its `Sites:` line says `2 | read src/api/orders.ts and src/api/users.ts`. The key needs at least 5, the count `git grep` gives. The playbook asks for every site of a pattern by command, and two sites you read are a sample.
- **K3, line window.** Run 1 has a test comment on `auth.test.ts:24`, about clock skew. That is 6 lines from the key's line 18, outside the 3-line window, and it names a different gap. The scorer reports no comment near line 18.
- K1 is found. The comment names `exp` and `401`, which meets `exp | reject/401` through the second word of the `a/b` term.

Run 2 replaces the skew question with a `should fix` on line 18 that names the missing no-`exp` test, and counts the raw `fetch` calls with `git grep`.

Output of `python3 check/score_case.py cases/auth-header/key.md cases/auth-header/runs/run-1/drafts.md` (exit 1):

```
K1 web-gateway#88 found
K2 admin-ui#41 MISSED Sites 2, key needs at least 5
K3 web-gateway#88 MISSED no comment on src/middleware/auth.test.ts near line 18
FAIL 1/3 key findings
```

Output of `python3 check/score_case.py cases/auth-header/key.md cases/auth-header/runs/run-2/drafts.md` (exit 0):

```
K1 web-gateway#88 found
K2 admin-ui#41 found
K3 web-gateway#88 found
PASS 3/3 key findings
```
