import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All required settings raise a clear validation error at startup if unset,
    instead of failing deep inside a request handler.
    """

    # Kept only so existing env files keep loading; the API no longer opens a
    # PostgREST client (migration 004 revoked the anon key's table access and
    # every endpoint now runs on the scoped Postgres roles below).
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_api_key: str = ""
    supabase_project_id: str = ""
    # Kept so existing env files continue to load. Normal search no longer uses
    # OPENAI_KEY; it always goes through the deterministic HiveBlot bio_query
    # parser. OpenAI-compatible extraction, if enabled, reads env vars directly.
    openai_key: str = ""

    # Connection string for a Postgres role that only has SELECT on
    # western_blot_records. Used exclusively to execute the LLM-generated
    # SQL from /search and /v1/search, so a bug in sql_guard can't turn into
    # a full-database compromise the way it could with the Supabase
    # service-role key.
    db_readonly_url: str

    # Connection string for the hive_feedback role (migration 002): INSERT +
    # SELECT on hiveblot_feedback ONLY. Separate from db_readonly_url so the
    # feedback write path physically cannot touch western_blot_records —
    # researcher corrections are stored beside, never over, the AI extraction.
    # Optional: when empty, the feedback endpoints return 503 instead of the
    # whole API failing to boot.
    db_feedback_url: str = ""

    # Shared secret the web/ frontend's server-side API route uses to call
    # the internal endpoints (/search, /proteins). Only ever sent server-to-
    # server (Next.js route handler -> this API), never to the browser.
    internal_api_key: str

    # Comma-separated list of API keys allowed to call the external,
    # agent-facing endpoint (/v1/search). A list, not a single shared secret,
    # so each agent/integration can be issued and revoked independently
    # without rotating everyone else's key.
    agent_api_keys: str

    # Comma-separated list of exact origins allowed to call the internal API.
    # Irrelevant to /v1/search (server-to-server agent calls, not browser
    # requests), but still enforced for the internal endpoints.
    allowed_origins: str = "http://localhost:3000"

    # slowapi rate-limit strings, e.g. "20/minute"
    search_rate_limit: str = "20/minute"
    agent_rate_limit: str = "10/minute"
    # Feedback gets its own, generous bucket (F-6): every hosted researcher
    # arrives from the same Vercel proxy IP, so the key is effectively "all of
    # UCSF" — sharing the search limit silently dropped real feedback.
    feedback_rate_limit: str = "120/minute"
    # Hard ceiling on paid model work per UTC day, across all users: live
    # extractions (one model call per panel) and paper-QA answers.
    daily_ingest_cap: int = 30
    daily_ask_cap: int = 200
    # Live extractions running at once in the API process (others queue).
    ingest_concurrency: int = 1

    # Stamped on every feedback row and returned by /health, so a demo laptop
    # and a hosted deployment are distinguishable in the F-1 export (F-5,
    # replacing the hardcoded "beta-local"). Set APP_VERSION explicitly, or
    # let it fall back to the build SHA Render injects by itself.
    app_version: str = os.environ.get("RENDER_GIT_COMMIT", "dev-local")[:12]

    table_name: str = "western_blot_records"
    max_search_limit: int = 500

    # --- EXPERIMENTAL (live ingestion / discovery / paper QA / densitometry) --
    experimental_enabled: bool = True
    # Unreviewed tier written by live DOI ingestion (migration 005).
    live_table_name: str = "western_blot_records_live"
    # hive_ingest role DSN (INSERT/DELETE on the live tables only). Empty =>
    # ingestion endpoints return 503; search over the live table still works.
    db_ingest_url: str = ""
    # Valency Bond bearer token (Settings page in app.valency.io). Server-only.
    valency_api_token: str = ""
    valency_mcp_url: str = "https://mcp.valency.io/"

    # Base directory the figure-crop endpoint may serve PNGs from. Records
    # store absolute crop paths (image_crop_ref); only paths resolving inside
    # this directory are ever served. Default = the local pipeline's run dir.
    crop_base_dir: str = str(
        Path(__file__).resolve().parents[2] / "western_blot_miner" / "data" / "pdf_runs"
    )

    # Kept for backwards-compatible env loading; not used by normal search.
    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def agent_api_keys_set(self) -> set[str]:
        return {k.strip() for k in self.agent_api_keys.split(",") if k.strip()}


settings = Settings()
