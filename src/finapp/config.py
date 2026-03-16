"""Application configuration — all settings loaded from environment variables.

Guardrail GRD-SEC-001: API keys are NEVER hardcoded here. They are read from
.env via pydantic-settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    All values are loaded from environment variables or a .env file.
    See .env.example for documentation of each key.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # AI Provider
    # -------------------------------------------------------------------------
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Claude model to use for all agents",
    )
    agent_max_tokens: int = Field(default=4096)
    agent_temperature: float = Field(default=0.3, ge=0.0, le=1.0)

    # -------------------------------------------------------------------------
    # Market Data
    # -------------------------------------------------------------------------
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API key")
    alpha_vantage_base_url: str = Field(default="https://www.alphavantage.co/query")
    alpha_vantage_rate_limit_per_minute: int = Field(default=5)

    # -------------------------------------------------------------------------
    # News
    # -------------------------------------------------------------------------
    news_api_key: str = Field(default="", description="NewsAPI.org key")
    news_api_base_url: str = Field(default="https://newsapi.org/v2")

    # -------------------------------------------------------------------------
    # Web Search
    # -------------------------------------------------------------------------
    brave_search_api_key: str = Field(default="", description="Brave Search API key")
    brave_search_base_url: str = Field(default="https://api.search.brave.com/res/v1/web/search")

    # -------------------------------------------------------------------------
    # Database
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="sqlite+aiosqlite:///./finapp.db",
        description="SQLAlchemy async database URL",
    )

    # -------------------------------------------------------------------------
    # Cache
    # -------------------------------------------------------------------------
    cache_dir: str = Field(default=".cache")
    cache_ttl_quote_seconds: int = Field(default=300)       # 5 minutes
    cache_ttl_historical_seconds: int = Field(default=3600)  # 1 hour
    cache_ttl_fundamentals_seconds: int = Field(default=86400)  # 24 hours
    cache_ttl_news_seconds: int = Field(default=1800)       # 30 minutes

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    default_benchmark: str = Field(default="SPY")
    risk_free_rate_annual: float = Field(default=0.05, description="Annual risk-free rate")
    default_currency: str = Field(default="USD")
    large_position_threshold_pct: float = Field(
        default=10.0,
        description="Warn when a position exceeds this % of portfolio",
    )


# Module-level singleton — import this throughout the app
settings = Settings()  # type: ignore[call-arg]
