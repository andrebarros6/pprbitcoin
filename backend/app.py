"""
PPR Bitcoin API - Main application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from database import init_db
from api.routes import ppr, bitcoin, portfolio


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    print("[START] Starting PPR Bitcoin API...")
    init_db()
    print("[OK] Database initialized")
    yield
    # Shutdown
    print("[STOP] Shutting down PPR Bitcoin API...")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

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
