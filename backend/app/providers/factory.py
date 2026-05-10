from app.config import get_settings
from .base import MarketDataProvider
from .mock_provider import MockMarketDataProvider
from .upstox_provider import UpstoxMarketDataProvider


def get_market_provider() -> MarketDataProvider:
    settings = get_settings()
    provider = settings.data_provider.lower().strip()
    if provider == "mock":
        return MockMarketDataProvider()
    if provider == "upstox":
        return UpstoxMarketDataProvider(settings.upstox_base_url, settings.upstox_access_token)
    raise ValueError(f"Unsupported DATA_PROVIDER={settings.data_provider}")
