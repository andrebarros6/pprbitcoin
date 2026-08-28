"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings


def _engine_kwargs() -> dict:
    """
    SQLite (used for local development and tests) rejects the pooling
    arguments that Postgres needs, so they are only applied for Postgres.
    """
    if settings.sqlalchemy_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_size": 10, "max_overflow": 20}


# Create database engine
engine = create_engine(
    settings.sqlalchemy_url,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    **_engine_kwargs(),
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Used with FastAPI's dependency injection.

    Yields:
        Session: Database session

    Example:
        @app.get("/pprs")
        def get_pprs(db: Session = Depends(get_db)):
            return db.query(PPR).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    Should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)
