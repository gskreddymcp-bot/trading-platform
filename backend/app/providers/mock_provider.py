import math
import random
from datetime import datetime
from app.schemas import Quote, OptionChainLevel
from .base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self) -> None:
        self._base_prices = {
            "NSE_INDEX|Nifty 50": 22550.0,
            "NSE_INDEX|Nifty Bank": 48200.0,
        }

    def _symbol_from_key(self, key: str) -> str:
        if "Nifty 50" in key:
            return "NIFTY"
        if "Nifty Bank" in key:
            return "BANKNIFTY"
        return key.split("|")[-1].replace("INE", "STK")[:14]

    async def get_quotes(self, instrument_keys: list[str]) -> list[Quote]:
        quotes: list[Quote] = []
        now_seed = int(datetime.utcnow().timestamp() // 60)
        random.seed(now_seed)

        for idx, key in enumerate(instrument_keys):
            base = self._base_prices.get(key, 1000 + idx * 37)
            drift = random.uniform(-0.6, 0.8)
            noise = random.uniform(-0.004, 0.004)
            ltp = round(base * (1 + noise) + drift, 2)
            open_price = round(base * (1 + random.uniform(-0.003, 0.003)), 2)
            close = round(base * (1 + random.uniform(-0.005, 0.005)), 2)
            high = round(max(ltp, open_price, close) * (1 + random.uniform(0, 0.003)), 2)
            low = round(min(ltp, open_price, close) * (1 - random.uniform(0, 0.003)), 2)
            vwap = round((high + low + ltp) / 3, 2)
            volume = random.randint(100_000, 10_000_000)
            quotes.append(
                Quote(
                    symbol=self._symbol_from_key(key),
                    instrument_key=key,
                    ltp=ltp,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                    vwap=vwap,
                    raw={"provider": "mock"},
                )
            )
        return quotes

    async def get_option_chain(self, underlying_key: str, expiry_date: str) -> tuple[float, list[OptionChainLevel]]:
        quote = (await self.get_quotes([underlying_key]))[0]
        spot = quote.ltp
        step = 50 if "Nifty 50" in underlying_key else 100
        atm = round(spot / step) * step
        levels = []

        random.seed(int(datetime.utcnow().timestamp() // 60) + int(atm))
        for i in range(-10, 11):
            strike = atm + i * step
            distance = abs(strike - spot) / step

            call_base = max(1000, 80_000 / (1 + math.exp(-(strike - spot) / (3 * step))))
            put_base = max(1000, 80_000 / (1 + math.exp((strike - spot) / (3 * step))))

            call_oi = round(call_base + random.randint(0, 25000))
            put_oi = round(put_base + random.randint(0, 25000))

            # Push clear support and resistance into mock data
            if strike == atm - step:
                put_oi += 70000
            if strike == atm + (2 * step):
                call_oi += 80000

            call_prev = max(0, call_oi - random.randint(-10000, 20000))
            put_prev = max(0, put_oi - random.randint(-10000, 20000))

            levels.append(
                OptionChainLevel(
                    strike=float(strike),
                    call_oi=float(call_oi),
                    put_oi=float(put_oi),
                    call_prev_oi=float(call_prev),
                    put_prev_oi=float(put_prev),
                    call_change_oi=float(call_oi - call_prev),
                    put_change_oi=float(put_oi - put_prev),
                    call_volume=float(random.randint(1000, 100000)),
                    put_volume=float(random.randint(1000, 100000)),
                    call_iv=round(10 + distance + random.uniform(-1, 2), 2),
                    put_iv=round(10 + distance + random.uniform(-1, 2), 2),
                    call_ltp=round(max(1, spot - strike) + 100 / (1 + distance), 2),
                    put_ltp=round(max(1, strike - spot) + 100 / (1 + distance), 2),
                )
            )
        return spot, levels

    async def get_global_context(self) -> dict:
        random.seed(int(datetime.utcnow().timestamp() // 300))
        score = random.choice([-2, -1, 0, 1, 2])
        if score > 0:
            mood = "risk_on"
            drivers = ["US futures positive", "Crude stable", "Bitcoin firm"]
            warnings = []
        elif score < 0:
            mood = "risk_off"
            drivers = ["US futures weak", "Dollar firm", "Crude elevated"]
            warnings = ["Reduce long-side confidence until Indian market confirms"]
        else:
            mood = "neutral"
            drivers = ["Mixed global cues", "No dominant macro driver"]
            warnings = ["Wait for local market structure"]
        return {"global_risk_mood": mood, "score": float(score), "drivers": drivers, "warnings": warnings}
