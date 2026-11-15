import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.csrf import CSRFHeaderMiddleware

log = logging.getLogger("servixe")

if settings.sentry_dsn:
    import sentry_sdk  # optional dependency: pip install sentry-sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.env, traces_sample_rate=0.1, send_default_pii=False)


def create_app() -> FastAPI:
    from app.modules.admin import router as admin_r
    from app.modules.approvals import router as approvals_r
    from app.modules.assignments import router as assign_r
    from app.modules.billing import router as billing_r
    from app.modules.catalogue import router as catalogue_r
    from app.modules.enquiries import router as enq_r
    from app.modules.evidence import router as evidence_r
    from app.modules.families import router as families_r
    from app.modules.identity import router as identity_r
    from app.modules.incidents import router as incidents_r
    from app.modules.notifications import router as notif_r
    from app.modules.providers import router as providers_r
    from app.modules.requests import router as requests_r

    app = FastAPI(title=settings.app_name, version="1.0.0", docs_url=None if settings.is_production else "/docs",
                  redoc_url=None, openapi_url=None if settings.is_production else "/openapi.json")
    app.add_middleware(CSRFHeaderMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Requested-With"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse({"detail": "Internal server error"}, status_code=500)

    p = settings.api_prefix
    for r in (identity_r.router, enq_r.public, catalogue_r.public, catalogue_r.admin, families_r.portal, families_r.admin,
              requests_r.portal, requests_r.admin, approvals_r.admin, approvals_r.portal, assign_r.admin, assign_r.provider_api,
              evidence_r.router, incidents_r.admin, incidents_r.provider_api, billing_r.admin, billing_r.portal, billing_r.webhooks,
              notif_r.admin, notif_r.webhooks, providers_r.admin, providers_r.self_api, enq_r.admin, admin_r.router):
        app.include_router(r, prefix=p)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"status": "ok"}

    @app.get(f"{p}/meta")
    def meta():
        return {"name": "Servixe", "emergency_notice": settings.emergency_notice}

    return app


app = create_app()
