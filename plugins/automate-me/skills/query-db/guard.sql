-- Write-capable-login guard for query-db.
-- Counts the tables, views and foreign tables in non-system schemas that the
-- current login can INSERT, UPDATE, DELETE or TRUNCATE. A read-only login returns 0.
-- Superusers and members of pg_write_all_data return more than 0 when any table exists.
-- One statement, one row, one column, so it runs the same through psql or a Postgres MCP server.
SELECT count(*) AS writable_tables
FROM pg_catalog.pg_class c
JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r', 'p', 'v', 'f')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname NOT LIKE 'pg\_toast%'
  AND n.nspname NOT LIKE 'pg\_temp%'
  AND (   has_table_privilege(c.oid, 'INSERT')
       OR has_table_privilege(c.oid, 'UPDATE')
       OR has_table_privilege(c.oid, 'DELETE')
       OR has_table_privilege(c.oid, 'TRUNCATE'));
