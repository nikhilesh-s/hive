PARKED UNTIL AFTER THE UCSF DEMO
These Supabase items came from emails received September 1, 2026. Do not make database, security, billing, deployment, or infrastructure changes from this ticket until Nik explicitly asks. Before fixing anything later, verify the current Supabase state because some of the September 1 security findings may already have been resolved by subsequent HiveBlot security work.

# Supabase Follow-Up Ticket

## Project

- Project name: `srushtismadhure's Project`
- Organization: `HiveBlot`
- Supabase project ID: `zafombwswztvnjikcsdm`
- Alerts received: September 1, 2026

## Ticket 1 — Security Advisor Alerts

Supabase emailed with the subject `Action required: security vulnerabilities detected in your projects`. The email reported two critical issues.

**A. Table publicly accessible.**
Supabase description: "Anyone with your project URL can read, edit, and delete all data in this table because Row-Level Security is not enabled."
Advisor identifier: `rls_disabled_in_public`

**B. Sensitive data publicly accessible.**
Supabase description: "A table with columns that likely contain sensitive data (like passwords or personal identifiers) is accessible through the API without any access restrictions."
Advisor identifier: `sensitive_columns_exposed`

**Important current-state caveat.** Do not assume these alerts are still active. The HiveBlot repo/HANDOFF contains later security work involving RLS, restricted database roles, and access-matrix testing. When this ticket is eventually worked:

1. Check the current Supabase Security Advisor first.
2. Identify exactly which table(s), if any, still trigger either warning.
3. Compare that state against migrations already present in the repo.
4. Only make changes if a vulnerability is genuinely still present.
5. Do not blindly reapply old RLS/security fixes.

No action now.

## Ticket 2 — Automatic Project Pausing

Supabase also emailed with the subject `Your Supabase Project srushtismadhure's Project is going to be paused.`

Reason: Supabase detected insufficient activity for more than 7 days. The project was not yet paused when the email was sent; Supabase said it would automatically pause if inactivity continued. If paused, it can be unpaused from the Supabase dashboard within 90 days. Supabase says upgrading the organization to Pro prevents future automatic pausing.

Future questions, when we revisit this:

1. Is this Supabase project currently active or paused?
2. Is this still the production/current HiveBlot database?
3. Does normal HiveBlot usage provide enough activity to avoid pausing?
4. Do we actually need a paid Supabase plan, or is manually unpausing acceptable for the project's current stage?
5. Is any deployment depending on this database in a way that makes automatic pausing unacceptable?

No billing upgrade or infrastructure action now.

## Priority

After UCSF demo. These items do not precede: demo readiness, `DEMO.md`, UCSF presentation rehearsal. Do not work on them unless Nik explicitly asks.

## Repo evidence that the September 1 security alert may already be addressed (documentation cross-check only)

- `migrations/004_secure_public_tables.sql` (Supabase-history copy: `supabase/migrations/20260901000005_secure_hiveblot_public_tables.sql`) is dated 2026-09-01 in its header, states that RLS was found disabled on both application tables with anon/authenticated holding full CRUD, and declares an end state of RLS on with anon/authenticated revoked, `hive_readonly` SELECT on `western_blot_records` only, and `hive_feedback` INSERT+SELECT on `hiveblot_feedback` only.
- `HANDOFF.md` line 30 records "migration 004 applied 2026-09-01; 5/5 migrations in remote history; Security Advisor 0 errors (1 WARN: pg_trgm in public, deferred)"; line 230 repeats "Security Advisor 0 ERROR (1 WARN pg_trgm, deferred)" alongside "RLS on both tables" and "anon key 401 on read and insert".
- `HANDOFF.md` line 54 describes the migration as a P0 security fix verified live (anon key gets 401 on read/insert/update/delete), and lines 60-73 document the role/policy matrix (`hive_readonly_select_records`, `hive_feedback_insert_feedback`, `hive_feedback_select_feedback`; neither hive role is superuser/createrole/createdb/bypassrls). Commit `beaec0f` "Harden Supabase table access with RLS and scoped roles" is listed at line 1530.
- `api/tests/test_db_access_matrix.py` (docstring: "Database access matrix for the two application tables (migration 004)") contains `test_rls_enabled_on_both_tables`, `test_policies_target_explicit_roles`, `test_public_client_roles_have_no_access`, `test_public_client_roles_get_no_future_tables`, `test_hive_readonly_reads_records_only`, `test_hive_feedback_is_insert_and_read_only_on_feedback`, `test_hive_roles_are_not_privileged`, and `test_down_migration_is_reversible`.
- `migrations/005_experimental_live_tables.sql` (Supabase copy `20260905000006_experimental_live_tables.sql`) adds the `hive_ingest` role with RLS on the live tier per `HANDOFF.md` line 197; `test_live_tier_matrix` in the same test file covers it.
- This is documentary evidence only, not a verification of the live project. The Security Advisor must be re-checked before any action.

## Status check — 2026-09-09 (read-only, requested by Nik after the UCSF meeting)

Checked through the Supabase Management API and `supabase db query --linked`
(no changes made):

- Project `zafombwswztvnjikcsdm` status: **ACTIVE_HEALTHY** (not paused), Postgres 17.6, us-east-1.
- Security Advisor: **0 errors, 1 warning** (`extension_in_public`: `pg_trgm`, deferred on purpose). Neither `rls_disabled_in_public` nor `sensitive_columns_exposed` is present any more.
- `pg_tables.rowsecurity` is `true` for both `public.western_blot_records` and `public.hiveblot_feedback`.
- Row counts: 475 reviewed records; 1 feedback row (2026-08-18, a pre-launch test).

Conclusion: Ticket 1 is resolved by migration 004 (verified live). Ticket 2 is not currently active; the 7-day inactivity risk remains while beta traffic is low, so the open questions above still stand.
