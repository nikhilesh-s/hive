from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import settings
from .limiter import limiter
from .routers import external, internal

app = FastAPI(
    title="Hive API",
    version="0.1.0",
    description=(
        "Internal endpoints (/, /health, /proteins, /search) back the Hive "
        "web frontend only. /v1/search is the stable, documented endpoint "
        "for external agents/integrations - see its description in this "
        "OpenAPI schema for how to call it."
    ),
    # Not public: the schema lists every internal and experimental route.
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS applies to browser requests. It's meaningful for the internal API
# (called from web/'s server, but locking it down costs nothing) and largely
# irrelevant to /v1/search, which is meant to be called server-to-server by
# agents, not from a browser - auth (require_agent_key) is what actually
# guards that endpoint.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Pdf-Rights"],
)

app.include_router(internal.router)
app.include_router(external.router)

if settings.experimental_enabled:
    # Live ingestion / discovery / paper QA / densitometry. Internal-key only.
    from .experimental.densitometry_router import router as densitometry_router
    from .experimental.router import router as experimental_router

    app.include_router(experimental_router)
    app.include_router(densitometry_router)
    from .experimental.uploads import router as upload_router, ticket_router
    app.include_router(ticket_router)
    app.include_router(upload_router)

    # Local-runner bridge: hosted HiveBlot can ask the researcher's own machine
    # to run model jobs, so no Claude credential ever lives in the cloud. These
    # routes authenticate with HIVEBLOT_RUNNER_TOKEN, never the internal key,
    # and are inert (503) until that token is set.
    from .experimental import relay_client
    from .experimental.runner import router as runner_router

    app.include_router(runner_router)
    relay_client.install()
