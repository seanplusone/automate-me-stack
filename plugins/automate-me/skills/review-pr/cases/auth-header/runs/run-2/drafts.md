# PR review: bearer tokens for the admin app

A token with no expiry claim is accepted forever. The admin app still sends some requests without the new header.

## acme/web-gateway#88 | hold: accepts a token with no expiry claim as valid forever
About: Replaces the admin session cookie check with a signed bearer token check.
Changes: 2 files: 1 source, 1 test

### blocking | src/middleware/auth.ts:31 | https://github.com/acme/web-gateway/pull/88/files#diff-ffadd6d72f4f9b739e0eae864423032b922aa491a4384fd3f422481794779c21R31
`claims.exp && claims.exp < now` skips the expiry check when `exp` is missing, so such a token never expires. Can this reject a token with no `exp` with 401?
Plain: The check only looks at the expiry time when the token has one. A token signed without an expiry works forever, so a leaked token can never be cut off.
Evidence: A token signed with no `exp` got 200 from `/admin/users` in a local run.
Step: measured | A client sends a validly signed token with no `exp` claim.
Step: measured | `claims.exp` is undefined, so the expiry branch is skipped.
Step: measured | The request reaches `/admin/users` and gets 200.

### should fix | src/middleware/auth.test.ts:18 | https://github.com/acme/web-gateway/pull/88/files#diff-0a95b495c602bcc47fa0bfdac6a4bd2264200a7daef400a76f5014add9c5e2bcR18
These cases send a valid token and a bad signature. None sends a token with no `exp`, so the gap on `auth.ts` line 31 passes CI. Can you add that case and expect 401?
Plain: The new tests only try a good token and a forged one. Nothing tries a token without an expiry time, so the bug in the other comment would pass CI.
Evidence: Deleting the expiry check in `auth.ts` left all 6 tests green.
Step: measured | Delete the `exp` comparison in `auth.ts`.
Step: measured | Run the middleware tests; all 6 pass.

Body: Merge together with [admin-ui#41](https://github.com/acme/admin-ui/pull/41), since either one alone signs admins out.

## acme/admin-ui#41 | approve after the raw fetch calls go through the shared client
About: Makes the admin app send its sign-in token as a bearer header on every API call.
Changes: 3 files: 3 source

### should fix | src/api/orders.ts:12 | https://github.com/acme/admin-ui/pull/41/files#diff-471259075281cf3203e6c61dcf4259f2c1ac453e16fb963eba0eaf238a3cf167R12
This `fetch` sends cookies but no `Authorization` header, so it gets 401 once [web-gateway#88](https://github.com/acme/web-gateway/pull/88) drops sessions. Can it use `apiClient` from `client.ts`?
Plain: Most calls now go through the shared client that adds the token, but five still call `fetch` directly. After the gateway change they would fail, and pages such as the orders list would show as empty.
Step: measured | `git grep` finds `listOrders()` calling raw `fetch` with no header.
Step: inferred | The gateway finds no bearer header and returns 401.
Sites: 5 | git grep -n 'fetch(' pr-41 -- src/api/ ':!src/api/client.ts'

### should fix | src/api/users.ts:20 | https://github.com/acme/admin-ui/pull/41/files#diff-6f0d613fc0498e89708e9b3feb7ac2047393de79a5288be4447da67a2cc45a21R20
This `fetch` sends cookies but no `Authorization` header, so it gets 401 once [web-gateway#88](https://github.com/acme/web-gateway/pull/88) drops sessions. Can it use `apiClient` from `client.ts`?

Body: Approve once the raw `fetch` calls use the shared client. The comments are inline.

## Totals
Refuter: checked 5, reworded 3, dropped 1.
