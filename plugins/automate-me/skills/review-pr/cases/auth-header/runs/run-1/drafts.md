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

### question | src/middleware/auth.test.ts:24 | https://github.com/acme/web-gateway/pull/88/files#diff-0a95b495c602bcc47fa0bfdac6a4bd2264200a7daef400a76f5014add9c5e2bcR24
This test checks a token that expired an hour ago. Can one more case cover a token that expires a second from now, for the skew allowance?

Body: Merge together with [admin-ui#41](https://github.com/acme/admin-ui/pull/41), since either one alone signs admins out.

## acme/admin-ui#41 | approve after the raw fetch calls go through the shared client
About: Makes the admin app send its sign-in token as a bearer header on every API call.
Changes: 3 files: 3 source

### should fix | src/api/orders.ts:12 | https://github.com/acme/admin-ui/pull/41/files#diff-471259075281cf3203e6c61dcf4259f2c1ac453e16fb963eba0eaf238a3cf167R12
This `fetch` sends cookies but no `Authorization` header, so it gets 401 once [web-gateway#88](https://github.com/acme/web-gateway/pull/88) drops sessions. Can it use `apiClient` from `client.ts`?
Plain: Most calls now go through the shared client that adds the token, but this one still calls `fetch` directly. After the gateway change it would fail, and the orders page would show as empty.
Step: inferred | The orders page calls `listOrders()`, which uses raw `fetch`.
Step: inferred | The gateway finds no bearer header and returns 401.
Sites: 2 | read src/api/orders.ts and src/api/users.ts

### should fix | src/api/users.ts:20 | https://github.com/acme/admin-ui/pull/41/files#diff-6f0d613fc0498e89708e9b3feb7ac2047393de79a5288be4447da67a2cc45a21R20
This `fetch` sends cookies but no `Authorization` header, so it gets 401 once [web-gateway#88](https://github.com/acme/web-gateway/pull/88) drops sessions. Can it use `apiClient` from `client.ts`?

Body: Approve once the raw `fetch` calls use the shared client. The comments are inline.

## Totals
Refuter: checked 5, reworded 2, dropped 0.
