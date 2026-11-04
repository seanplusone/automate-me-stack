# Reference: frontend

Load for `.ts`, `.tsx`, `.js` or `.jsx` changes, and for a `<script>` added to a server-rendered template. For `.ts`/`.tsx`, also read pstack's `typescript-best-practices` skill if it is installed. The facts live in the repo. Read its `package.json`, `tsconfig` and store setup at the base commit before you call anything a pattern.

## Risk classes

**Which React.** One repo can hold more than one floor. An old package may run React 15 on Babel 6 next to apps on React 18 or 19, or a Vue app beside them. Read the nearest `package.json` and Babel or TypeScript config before suggesting a fix. On an old floor there may be no hooks, no `<>` fragments and no optional chaining. A fix that uses any of them is a wrong fix.

**The shared API layer.** The apps may share one API client, such as an RTK Query `api` instance, a shared `fetch` wrapper or a generated SDK. Then a change to its base query, the auth header, the tag list or a shared type reaches every app. Grep the consumers across the repo and say which were checked.

**Cache tags.** A mutation needs `invalidatesTags` (or the library's equivalent, such as `queryClient.invalidateQueries`) that match every query showing the data it changes, or the screen goes stale until reload. Check new endpoints against the tag list. A tag nobody provides invalidates nothing.

**Who serves the URL.** Find the server route for every URL a new endpoint calls, in the backend the browser actually reaches in production. A dev proxy can route a call to a service the browser never reaches in production, so the screen works locally and fails after deploy.

**Hand-written types.** When API types are written by hand, nothing checks them at runtime. Diff each new or changed response type against what the backend handler returns. A mismatch types fine and fails on the screen. Check whether `strict` or `noImplicitAny` is off in `tsconfig`. New `any`, `as` casts and `@ts-ignore` hide the same drift.

**Store hygiene.** No state change outside a reducer or Immer draft. If `serializableCheck` is off, a non-serializable value (Date, class instance, function) gets in silently and comes back as something else after a persisted store rehydrates. Selectors that build a new array or object need `createSelector`, or every render rerenders.

**Effects and auth.** `useEffect` dependencies that miss a value read inside, and closures over stale state. When the token lives in `localStorage`, `dangerouslySetInnerHTML` or an unescaped HTML string is a token-theft path, not just XSS. A new fetch that skips the shared auth header is a finding.

**JS inside a server-rendered template.** A `<script>` in a server template (Blade, Jinja, ERB, JSP) runs in the browser but ships with the backend app. The React rules here do not apply, and the backend's CI often has no Node or browser, so its tests can only read the script as text. To see the script run, load it from a `file://` page in headless Chrome with the repo's vendored copy of each library it uses, never against a shared environment.

## Running things

Find out what tests exist before writing "nothing covers this". If the frontend has none, the comment states a known fact, so don't write one. Measure with what exists, in a worktree at the PR head:

- Type check: `npx tsc --noEmit -p <app or package>`. It works even where the package has no `typecheck` script.
- Lint: `npx eslint <changed files>`.
- Build: the app's build command (such as `npx vite build`), when the change touches config or imports.
- Tests: the app's own test command, when it has one, scoped to the changed files.

A type error the PR introduces is evidence. A type error already present at the base is not.
