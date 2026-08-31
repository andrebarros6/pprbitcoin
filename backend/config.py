"""
Configuration settings for PPR Bitcoin API
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    DATABASE_URL: str = "postgresql://pprbitcoin:pprbitcoin_dev_password@localhost:5432/pprbitcoin"

    # API Configuration
    API_VERSION: str = "v1"
    API_TITLE: str = "PPR Bitcoin API"
    API_DESCRIPTION: str = "API para análise de portfolios PPR + Bitcoin"
    # Defaults to False so a missing env var cannot accidentally expose
    # stack traces or turn on SQLAlchemy statement logging in production.
    DEBUG: bool = False

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:5173"

    # External APIs
    COINGECKO_API_KEY: str = ""
    KRAKEN_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Run the data-refresh scheduler inside the API process. Keep False when
    # running more than one instance, or the refresh runs once per instance.
    ENABLE_SCHEDULER: bool = False

    # Sentry (Error Monitoring). Blank disables it entirely, so local runs
    # and CI never report anywhere.
    SENTRY_DSN: str = ""
    # Tags events so production noise is distinguishable from a staging run.
    ENVIRONMENT: str = "development"
    # Fraction of requests traced for performance. Errors are always sent;
    # this only governs timing spans, which are the expensive part of the
    # free-tier quota.
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    # Timezone
    TZ: str = "Europe/Lisbon"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list"""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def sqlalchemy_url(self) -> str:
        """
        Normalise the database URL for SQLAlchemy.

        Railway (and Heroku) expose Postgres as `postgres://`, a scheme
        SQLAlchemy 2.x no longer recognises. Rewriting it here means the
        platform-provided DATABASE_URL can be used verbatim.
        """
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


# Singleton instance
settings = Settings()
