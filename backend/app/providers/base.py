from abc import ABC, abstractmethod
from app.schemas import Quote, OptionChainLevel


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quotes(self, instrument_keys: list[str]) -> list[Quote]:
        raise NotImplementedError

    @abstractmethod
    async def get_option_chain(self, underlying_key: str, expiry_date: str) -> tuple[float, list[OptionChainLevel]]:
        raise NotImplementedError

    @abstractmethod
    async def get_global_context(self) -> dict:
        raise NotImplementedError
