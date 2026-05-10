from datetime import date
import httpx

from app.schemas import Quote, OptionChainLevel
from .base import MarketDataProvider


class UpstoxMarketDataProvider(MarketDataProvider):
    def __init__(self, base_url: str, access_token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

        if not self.access_token:
            raise ValueError("UPSTOX_ACCESS_TOKEN is required when DATA_PROVIDER=upstox")

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

    async def get_quotes(self, instrument_keys: list[str]) -> list[Quote]:
        if not instrument_keys:
            return []

        url = f"{self.base_url}/v2/market-quote/quotes"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                params={"instrument_key": ",".join(instrument_keys)},
                headers=self._headers(),
            )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Upstox quote API failed: status={resp.status_code}, body={resp.text[:1000]}"
            )

        payload = resp.json()
        data = payload.get("data", {})

        parsed_by_key: dict[str, Quote] = {}

        for response_key, item in data.items():
            ohlc = item.get("ohlc", {}) or {}

            instrument_key = (
                item.get("instrument_token")
                or item.get("instrument_key")
                or response_key.replace(":", "|")
            )

            instrument_key = str(instrument_key)
            symbol = _symbol_from_instrument_key(instrument_key, response_key, item)

            ltp = item.get("last_price") or item.get("ltp") or ohlc.get("close")

            if ltp is None:
                continue

            parsed_by_key[instrument_key] = Quote(
                symbol=symbol,
                instrument_key=instrument_key,
                ltp=float(ltp),
                open=_to_float(ohlc.get("open")),
                high=_to_float(ohlc.get("high")),
                low=_to_float(ohlc.get("low")),
                close=_to_float(ohlc.get("close")),
                volume=_to_float(item.get("volume")),
                vwap=_to_float(item.get("average_price") or item.get("vwap")),
                raw=item,
            )

        ordered_quotes: list[Quote] = []
        missing: list[str] = []

        for key in instrument_keys:
            quote = parsed_by_key.get(key)
            if quote is None:
                missing.append(key)
            else:
                ordered_quotes.append(quote)

        if missing:
            raise RuntimeError(
                "Upstox quote API did not return requested instruments. "
                f"missing={missing}, returned={list(parsed_by_key.keys())}"
            )

        return ordered_quotes

    async def get_option_contract_expiries(self, underlying_key: str) -> list[str]:
        """
        Fetch active option-contract expiries for an underlying index.

        This avoids hardcoding weekly/monthly expiries in .env.
        """
        url = f"{self.base_url}/v2/option/contract"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                params={"instrument_key": underlying_key},
                headers=self._headers(),
            )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Upstox option contract API failed: status={resp.status_code}, body={resp.text[:1000]}"
            )

        payload = resp.json()
        rows = payload.get("data", [])

        expiries: set[str] = set()

        for row in rows:
            expiry = (
                row.get("expiry")
                or row.get("expiry_date")
                or row.get("expiryDate")
            )

            if expiry:
                expiries.add(str(expiry)[:10])

        clean_expiries = sorted(e for e in expiries if _looks_like_iso_date(e))

        if not clean_expiries:
            raise RuntimeError(
                "Upstox option contract API returned no usable expiries. "
                f"instrument_key={underlying_key}, body={str(payload)[:1000]}"
            )

        return clean_expiries

    async def resolve_option_expiry(
        self,
        underlying_key: str,
        preferred_expiry: str | None = None,
    ) -> str:
        """
        Use preferred expiry only if it exists in active contracts.
        Otherwise choose the nearest non-expired active expiry.
        """
        expiries = await self.get_option_contract_expiries(underlying_key)

        if preferred_expiry and preferred_expiry in expiries:
            return preferred_expiry

        today = date.today()

        future_expiries: list[str] = []

        for expiry in expiries:
            try:
                expiry_date = date.fromisoformat(expiry)
            except ValueError:
                continue

            if expiry_date >= today:
                future_expiries.append(expiry)

        if future_expiries:
            return sorted(future_expiries)[0]

        return expiries[0]

    async def get_option_chain(
        self,
        underlying_key: str,
        expiry_date: str,
    ) -> tuple[float, list[OptionChainLevel]]:
        url = f"{self.base_url}/v2/option/chain"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                params={
                    "instrument_key": underlying_key,
                    "expiry_date": expiry_date,
                },
                headers=self._headers(),
            )

        if resp.status_code >= 400:
            raise RuntimeError(
                f"Upstox option chain API failed: status={resp.status_code}, body={resp.text[:1000]}"
            )

        payload = resp.json()
        rows = payload.get("data", [])

        if not rows:
            raise RuntimeError(
                "Upstox option chain returned no rows. "
                f"instrument_key={underlying_key}, expiry_date={expiry_date}, body={str(payload)[:1000]}"
            )

        levels: list[OptionChainLevel] = []
        spot = 0.0

        for row in rows:
            spot = float(row.get("underlying_spot_price") or spot or 0.0)

            call = row.get("call_options") or {}
            put = row.get("put_options") or {}

            call_md = call.get("market_data") or {}
            put_md = put.get("market_data") or {}

            call_greeks = call.get("option_greeks") or {}
            put_greeks = put.get("option_greeks") or {}

            call_oi = _to_float(call_md.get("oi")) or 0.0
            put_oi = _to_float(put_md.get("oi")) or 0.0

            call_prev_oi = _to_float(call_md.get("prev_oi")) or 0.0
            put_prev_oi = _to_float(put_md.get("prev_oi")) or 0.0

            levels.append(
                OptionChainLevel(
                    strike=float(row["strike_price"]),
                    call_oi=call_oi,
                    put_oi=put_oi,
                    call_prev_oi=call_prev_oi,
                    put_prev_oi=put_prev_oi,
                    call_change_oi=call_oi - call_prev_oi,
                    put_change_oi=put_oi - put_prev_oi,
                    call_volume=_to_float(call_md.get("volume")) or 0.0,
                    put_volume=_to_float(put_md.get("volume")) or 0.0,
                    call_iv=_to_float(call_greeks.get("iv")),
                    put_iv=_to_float(put_greeks.get("iv")),
                    call_ltp=_to_float(call_md.get("ltp")),
                    put_ltp=_to_float(put_md.get("ltp")),
                )
            )

        return spot, levels

    async def get_global_context(self) -> dict:
        return {
            "global_risk_mood": "neutral",
            "score": 0.0,
            "drivers": ["Real global provider not configured yet"],
            "warnings": ["Global context is neutral placeholder in Upstox-only mode"],
        }


def _symbol_from_instrument_key(
    instrument_key: str,
    response_key: str,
    item: dict,
) -> str:
    if instrument_key == "NSE_INDEX|Nifty 50":
        return "NIFTY"

    if instrument_key == "NSE_INDEX|Nifty Bank":
        return "BANKNIFTY"

    symbol = item.get("symbol")

    if symbol and symbol != "NA":
        return str(symbol)

    return response_key.split(":")[-1]


def _to_float(value) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _looks_like_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False