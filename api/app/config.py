from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All required settings raise a clear validation error at startup if unset,
    instead of failing deep inside a request handler.
    """

    supabase_url: str
    supabase_key: str
    openai_key: str

    # Connection string for a Postgres role that only has SELECT on
    # western_blot_records. Used exclusively to execute the LLM-generated
    # SQL from /search and /v1/search, so a bug in sql_guard can't turn into
    # a full-database compromise the way it could with the Supabase
    # service-role key.
    db_readonly_url: str

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

    table_name: str = "western_blot_records"
    max_search_limit: int = 500

    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def agent_api_keys_set(self) -> set[str]:
        return {k.strip() for k in self.agent_api_keys.split(",") if k.strip()}


settings = Settings()
