# Key: auth-header

A synthetic case. The repos `acme/web-gateway` and `acme/admin-ui`, PRs #88 and #41, and every line number below are invented. Two linked PRs move the admin app from cookie sessions to bearer tokens. Never show this file to the skill.

web-gateway#88 replaces the session check in `src/middleware/auth.ts` (TypeScript, Express) with a JWT check, and adds `src/middleware/auth.test.ts`. admin-ui#41 makes the React app send `Authorization: Bearer <token>` through its shared client in `src/api/client.ts`. The body of #88 names #41 as its companion and says "Merge both together." The ticket is PROJ-456, "Admin users sign in with a token instead of a session cookie."

The input is the web-gateway#88 URL. Score against these heads:

- acme/web-gateway#88 at `0000000b2` (fake head)
- acme/admin-ui#41 at `0000000c3` (fake head)

## How to score

- Run `python3 check/score_case.py cases/auth-header/key.md <drafts.md>`. It checks that each finding has a comment in the right PR on the right path, within 3 lines of the row's Line when it names one. It also checks that the `Sites:` count reaches the minimum and that the comment names each `Terms:` word.
- A person then checks that each found comment names the same problem. Wording can differ.
- A comment with no evidence behind it is **unsupported** and counts as an error.
- The run passes the format only if `check/check_drafts.py` exits 0.

## Findings the skill should make

| ID | PR | Path | Line | Finding | Min sites | Proof |
|----|----|------|------|---------|-----------|-------|
| K1 | web-gateway#88 | `src/middleware/auth.ts` | 31 | `if (claims.exp && claims.exp < now)` lets a token with no `exp` claim through forever. A leaked token never stops working. | - | A test token signed with no `exp` gets 200 from `/admin/users`. |
| K2 | admin-ui#41 | `src/api/` | - | Five calls under `src/api/` still use raw `fetch` with `credentials: "include"` instead of the shared client. They send no bearer header, so they get 401 once #88 drops sessions. | 5 | `git grep -n 'fetch(' pr-41 -- src/api/ ':!src/api/client.ts'` lists 5 calls. |
| K3 | web-gateway#88 | `src/middleware/auth.test.ts` | 18 | The tests cover a valid token and a bad signature only. None sends a token with no `exp`, so K1 passes CI. | - | Deleting the `exp` check leaves every test green. |

Terms: K1 | exp | reject/401

Optional finds. A question or nit on these is fine, and missing them is not a miss.

- The clock-skew allowance is hard-coded as 300 seconds in two places.
- The PR body's rollout plan does not say how existing sessions end.

## Traps

- Saying `jwt.decode` skips the signature. The middleware calls `jwt.verify` with the public key; `decode` appears only in a log line.
- Approving admin-ui#41 because `client.ts` sets the header. The raw `fetch` calls never go through `client.ts`.
- Putting merge order in a verdict. "Merge together" belongs in the review body.
