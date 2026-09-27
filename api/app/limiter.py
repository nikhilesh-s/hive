import hmac

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import settings


def client_key(request: Request) -> str:
    """Rate-limit key: the researcher's IP, not the Vercel proxy's.

    Every hosted request arrives from the web app's server, so keying on the
    socket address put all researchers in one bucket. The web proxy forwards
    the browser's IP in X-Hive-Client-IP; it is trusted only when the request
    also carries the internal key (only our proxy has it), so a direct caller
    cannot pick its own bucket.
    """
    forwarded = request.headers.get("x-hive-client-ip", "").strip()
    auth = request.headers.get("authorization", "")
    if forwarded and settings.internal_api_key and hmac.compare_digest(
        auth.encode(), f"Bearer {settings.internal_api_key}".encode()
    ):
        return forwarded[:64]
    return get_remote_address(request)


# Single shared limiter instance so main.py and both routers reference the
# same rate-limit state instead of each creating their own.
limiter = Limiter(key_func=client_key)
