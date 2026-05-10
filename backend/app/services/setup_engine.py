from app.config import get_settings
from app.schemas import BiasResult, Quote, OptionChainAnalysis, TradeSetupOut


def generate_setups(
    bias: BiasResult,
    nifty: Quote,
    banknifty: Quote,
    nifty_options: OptionChainAnalysis,
    banknifty_options: OptionChainAnalysis,
) -> list[TradeSetupOut]:
    settings = get_settings()
    setups: list[TradeSetupOut] = []

    setups.extend(_index_setups("NIFTY", nifty, nifty_options, bias))
    setups.extend(_index_setups("BANKNIFTY", banknifty, banknifty_options, bias))

    # Basic risk filter
    filtered = []
    for setup in setups:
        if setup.risk_reward is not None and setup.risk_reward < settings.risk_reward_min:
            setup.decision = "reject"
            setup.reason.append(f"Risk-reward {setup.risk_reward} is below minimum {settings.risk_reward_min}")
        filtered.append(setup)

    priority = {"trade_only_on_trigger": 0, "wait_for_confirmation": 1, "reject": 2}
    filtered.sort(key=lambda x: priority.get(x.decision, 9))
    return filtered[: settings.max_setups_per_scan]


def _index_setups(symbol: str, quote: Quote, chain: OptionChainAnalysis, bias: BiasResult) -> list[TradeSetupOut]:
    out: list[TradeSetupOut] = []
    step = 100 if symbol == "BANKNIFTY" else 50

    support = chain.support_zones[0] if chain.support_zones else quote.low
    resistance = chain.resistance_zones[0] if chain.resistance_zones else quote.high

    if "bullish" in bias.market_bias and quote.vwap and quote.ltp > quote.vwap and chain.signal in {"bullish", "neutral"}:
        entry = round(max(quote.high or quote.ltp, quote.ltp + step * 0.25), 2)
        stop = round(min(support or quote.vwap, quote.vwap), 2)
        target1 = round(entry + max(step, (entry - stop) * 1.5), 2)
        rr = _rr(entry, stop, target1, "long")
        out.append(
            TradeSetupOut(
                symbol=symbol,
                direction="long",
                setup_type="vwap_continuation_or_breakout",
                entry=entry,
                stop_loss=stop,
                target_1=target1,
                target_2=round(target1 + step, 2),
                risk_reward=rr,
                confidence=bias.confidence,
                decision="trade_only_on_trigger" if bias.confidence == "high" else "wait_for_confirmation",
                reason=[
                    f"{symbol} is above VWAP",
                    f"Option chain signal is {chain.signal}",
                    f"Nearest support zone: {support}",
                ],
                invalidation=[
                    f"{symbol} falls below VWAP",
                    "Fresh put unwinding starts near support",
                    "BANKNIFTY/NIFTY confirmation breaks",
                ],
            )
        )

    if "bearish" in bias.market_bias and quote.vwap and quote.ltp < quote.vwap and chain.signal in {"bearish", "neutral"}:
        entry = round(min(quote.low or quote.ltp, quote.ltp - step * 0.25), 2)
        stop = round(max(resistance or quote.vwap, quote.vwap), 2)
        target1 = round(entry - max(step, (stop - entry) * 1.5), 2)
        rr = _rr(entry, stop, target1, "short")
        out.append(
            TradeSetupOut(
                symbol=symbol,
                direction="short",
                setup_type="vwap_rejection_or_breakdown",
                entry=entry,
                stop_loss=stop,
                target_1=target1,
                target_2=round(target1 - step, 2),
                risk_reward=rr,
                confidence=bias.confidence,
                decision="trade_only_on_trigger" if bias.confidence == "high" else "wait_for_confirmation",
                reason=[
                    f"{symbol} is below VWAP",
                    f"Option chain signal is {chain.signal}",
                    f"Nearest resistance zone: {resistance}",
                ],
                invalidation=[
                    f"{symbol} recovers above VWAP",
                    "Call writing above spot unwinds aggressively",
                    "Global/local risk reverses",
                ],
            )
        )

    if not out:
        out.append(
            TradeSetupOut(
                symbol=symbol,
                direction="none",
                setup_type="no_trade_zone",
                entry=None,
                stop_loss=None,
                target_1=None,
                target_2=None,
                risk_reward=None,
                confidence="low",
                decision="wait",
                reason=[
                    f"{symbol} has no clean alignment between price, VWAP, bias, and option chain"
                ],
                invalidation=[
                    "Wait for price to break range with option-chain confirmation"
                ],
            )
        )

    return out


def _rr(entry: float, stop: float, target: float, direction: str) -> float | None:
    if direction == "long":
        risk = entry - stop
        reward = target - entry
    else:
        risk = stop - entry
        reward = entry - target

    if risk <= 0:
        return None
    return round(reward / risk, 2)
