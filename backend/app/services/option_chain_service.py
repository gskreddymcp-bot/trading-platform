from app.schemas import OptionChainAnalysis, OptionChainLevel


def analyze_option_chain(symbol: str, expiry: str, spot: float, levels: list[OptionChainLevel]) -> OptionChainAnalysis:
    if not levels:
        return OptionChainAnalysis(
            symbol=symbol,
            expiry=expiry,
            spot_price=spot,
            atm_strike=spot,
            pcr=0,
            reason=["No option chain data available"],
            warning=["Cannot analyze option chain"],
        )

    levels_sorted = sorted(levels, key=lambda x: x.strike)
    atm = min(levels_sorted, key=lambda x: abs(x.strike - spot)).strike

    total_call_oi = sum(x.call_oi for x in levels_sorted)
    total_put_oi = sum(x.put_oi for x in levels_sorted)
    pcr = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0.0

    support_candidates = [
        x for x in levels_sorted
        if x.strike <= spot and x.put_change_oi > 0
    ]
    resistance_candidates = [
        x for x in levels_sorted
        if x.strike >= spot and x.call_change_oi > 0
    ]

    support_zones = [
        x.strike for x in sorted(support_candidates, key=lambda x: (x.put_change_oi, x.put_oi), reverse=True)[:3]
    ]
    resistance_zones = [
        x.strike for x in sorted(resistance_candidates, key=lambda x: (x.call_change_oi, x.call_oi), reverse=True)[:3]
    ]

    call_unwinding_above = sum(abs(x.call_change_oi) for x in levels_sorted if x.strike >= spot and x.call_change_oi < 0)
    put_writing_below = sum(x.put_change_oi for x in levels_sorted if x.strike <= spot and x.put_change_oi > 0)
    call_writing_above = sum(x.call_change_oi for x in levels_sorted if x.strike >= spot and x.call_change_oi > 0)
    put_unwinding_below = sum(abs(x.put_change_oi) for x in levels_sorted if x.strike <= spot and x.put_change_oi < 0)

    score = 0
    reason: list[str] = []
    warning: list[str] = []

    if put_writing_below > call_writing_above * 0.75:
        score += 2
        reason.append("Fresh put writing below/near spot is supporting price")
    if call_unwinding_above > put_unwinding_below * 0.75 and call_unwinding_above > 0:
        score += 1
        reason.append("Call unwinding above spot supports bullish continuation")
    if call_writing_above > put_writing_below * 1.2:
        score -= 2
        reason.append("Fresh call writing above spot is creating resistance")
    if put_unwinding_below > call_unwinding_above * 1.2 and put_unwinding_below > 0:
        score -= 1
        reason.append("Put unwinding below spot weakens support")

    if pcr > 1.4:
        reason.append(f"PCR is elevated at {pcr}; bullish only if price confirms")
    elif pcr < 0.7:
        reason.append(f"PCR is low at {pcr}; bearish only if price confirms")
    else:
        reason.append(f"PCR is balanced at {pcr}")

    near_resistance = [z for z in resistance_zones if 0 <= z - spot <= (100 if symbol == "BANKNIFTY" else 50) * 2]
    if near_resistance:
        warning.append(f"Nearby call resistance at {near_resistance[0]}")

    if score >= 2:
        signal = "bullish"
    elif score <= -2:
        signal = "bearish"
    else:
        signal = "neutral"

    return OptionChainAnalysis(
        symbol=symbol,
        expiry=expiry,
        spot_price=round(spot, 2),
        atm_strike=float(atm),
        pcr=pcr,
        max_pain=_approx_max_pain(levels_sorted),
        support_zones=support_zones,
        resistance_zones=resistance_zones,
        signal=signal,
        reason=reason,
        warning=warning,
        levels=levels_sorted,
    )


def _approx_max_pain(levels: list[OptionChainLevel]) -> float | None:
    if not levels:
        return None

    strikes = [x.strike for x in levels]
    pain_by_strike = {}

    for expiry_price in strikes:
        pain = 0.0
        for row in levels:
            call_intrinsic = max(0.0, expiry_price - row.strike)
            put_intrinsic = max(0.0, row.strike - expiry_price)
            pain += call_intrinsic * row.call_oi
            pain += put_intrinsic * row.put_oi
        pain_by_strike[expiry_price] = pain

    return min(pain_by_strike, key=pain_by_strike.get)
