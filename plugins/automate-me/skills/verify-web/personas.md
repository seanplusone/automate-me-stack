# Personas

Who a verification run signs in as. A persona is a role in your app, plus the env var names that
hold its login. They are listed under `personas:` in `.claude/verify-web.yaml`. **Use the first
persona unless the task names another.** Sign in as another one only when the task says so, for
example "check a read-only user cannot edit this".

Logins live only in `~/.config/verify-web/users.env` (or the config's `users_env`), mode 600. The
user says which users exist and fills that file in. Never copy a password into this skill, a repo,
a report, a commit or a screenshot name. The file's shape is `users.env.example` next to this one.
The doctor warns when a persona has no login, or when the file is readable by others.

## The role matrix

Write down, for your app, which role or flag makes each persona what it is. One persona per
combination you need to tell apart. A typical set:

| Persona | What makes it that persona | Keys in `users.env` |
|---|---|---|
| `admin` | the admin role; can change any record and manage users | `ADMIN_*` |
| `regular` | a normal account with no special flags | `REGULAR_*` |
| `restricted` | can see only the records assigned to it; read-only off | `RESTRICTED_*` |
| `readonly` | can see everything and change nothing; restricted off | `READONLY_*` |

If your app has tenants, accounts or workspaces, add the tenant to the key (`ACME_ADMIN_*`) and
note which app URL each tenant signs in on.

Keep restricted and read-only on separate users. A user with both cannot tell you which flag
caused what you saw.

## When a login is missing or fails

Stop and ask the user for it, naming the persona and the app. Do not create users yourself unless
the user asks. When they do, create them through the app's own user screens, signed in as the
admin persona, never with SQL or a seed script. Write the login into `users.env` straight away,
and the persona into the config if it is new.
