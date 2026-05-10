from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Market Intelligence OS V1"
    app_env: str = "local"
    log_level: str = "INFO"

    data_provider: str = "mock"
    database_url: str = "sqlite:///./market_intel_os_v1.db"
    redis_url: str | None = None

    upstox_base_url: str = "https://api.upstox.com"
    upstox_access_token: str | None = None

    nifty_index_key: str = "NSE_INDEX|Nifty 50"
    banknifty_index_key: str = "NSE_INDEX|Nifty Bank"

    default_nifty_expiry: str = "2026-05-28"
    default_banknifty_expiry: str = "2026-05-27"

    scan_top_stock_limit: int = 100
    risk_reward_min: float = 1.5
    max_setups_per_scan: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
