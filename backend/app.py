"""
PPR Bitcoin API - Main application
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from config import settings
from database import init_db
from api.routes import ppr, bitcoin, portfolio
from utils.rate_limit import limiter

logger = logging.getLogger(__name__)


def _init_sentry() -> bool:
    """
    Start error reporting, if a DSN is configured.

    Runs before the app is created so that failures during startup -- a bad
    DATABASE_URL, a migration that will not apply -- are reported rather than
    disappearing into the platform log.

    Returns:
        True if Sentry was initialised.
    """
    if not settings.SENTRY_DSN:
        return False

    try:
        import sentry_sdk
    except ImportError:
        # The package is in requirements, but a missing optional dependency
        # must never stop the API from serving.
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed")
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.API_VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Request bodies carry portfolio parameters, not credentials, but
        # there is no reason to ship them to a third party to debug a stack
        # trace. send_default_pii stays off for the same reason: no IPs.
        max_request_body_size="never",
        send_default_pii=False,
    )
    return True


SENTRY_ENABLED = _init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    print("[START] Starting PPR Bitcoin API...")
    init_db()
    print("[OK] Database initialized")

    # Say so either way. Silent monitoring that is not actually reporting is
    # worse than none, because it is trusted.
    if SENTRY_ENABLED:
        print(f"[OK] Sentry error reporting active ({settings.ENVIRONMENT})")
    else:
        print("[..] Sentry disabled (no SENTRY_DSN set)")

    # The scheduler keeps Bitcoin and PPR data current. It is opt-in because
    # running it in every web instance would duplicate the refresh; with more
    # than one instance, run it as a separate worker instead.
    scheduler = None
    if settings.ENABLE_SCHEDULER:
        from services.scheduler import DataUpdateScheduler

        scheduler = DataUpdateScheduler()
        scheduler.start()
        print("[OK] Data refresh scheduler started")

    yield

    # Shutdown
    if scheduler is not None:
        scheduler.stop()
    print("[STOP] Shutting down PPR Bitcoin API...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Rate limiting (see utils/rate_limit.py)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(ppr.router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(bitcoin.router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(portfolio.router, prefix=f"/api/{settings.API_VERSION}")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "PPR Bitcoin API",
        "version": settings.API_VERSION,
        "docs": "/docs",
        "status": "online"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
