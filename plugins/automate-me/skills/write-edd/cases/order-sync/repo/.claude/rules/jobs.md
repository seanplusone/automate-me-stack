# Job rules

- Work that talks to an outside service runs in a job under src/Jobs, never inside a web request.
- A job sets the tenant with Context::setTenant before any model query.
- A job declares $tries and $backoff, and has a failed() method.
- Outgoing messages are stored as rows first, then a job delivers them in id order. See src/Jobs/DeliverWebhooks.php.
