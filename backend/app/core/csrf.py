"""CSRF defence for cookie-authenticated APIs: SameSite cookies + a required custom header on
state-changing requests (a custom header forces a CORS preflight, which only allow-listed origins pass)."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

SAFE = {"GET", "HEAD", "OPTIONS"}
EXEMPT_PREFIXES = ("/api/v1/webhooks/",)  # authenticated by signature instead of cookies


class CSRFHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method not in SAFE and not request.url.path.startswith(EXEMPT_PREFIXES):
            if request.headers.get("x-requested-with") != "Servixe":
                return JSONResponse({"detail": "Missing CSRF header"}, status_code=403)
        return await call_next(request)
