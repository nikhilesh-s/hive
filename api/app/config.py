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
    # SQL from /search, so a bug in sql_guard can't turn into a full-database
    # compromise the way it could with the Supabase service-role key.
    db_readonly_url: str

    # Shared-secret bearer token required on /search and /proteins.
    api_key: str

    # Comma-separated list of exact origins allowed to call this API.
    allowed_origins: str = "http://localhost:3000"

    # slowapi rate-limit string, e.g. "20/minute"
    search_rate_limit: str = "20/minute"

    table_name: str = "western_blot_records"
    max_search_limit: int = 500

    openai_model: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
