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
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # External APIs
    COINGECKO_API_KEY: str = ""
    KRAKEN_API_KEY: str = ""

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Sentry (Error Monitoring)
    SENTRY_DSN: str = ""

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
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Singleton instance
settings = Settings()
