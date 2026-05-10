from app.schemas import Quote, BreadthSummary, OptionChainAnalysis, GlobalContext, BiasResult


def calculate_market_bias(
    nifty: Quote,
    banknifty: Quote,
    breadth: BreadthSummary,
    nifty_options: OptionChainAnalysis,
    banknifty_options: OptionChainAnalysis,
    global_context: GlobalContext,
) -> BiasResult:
    score = 0.0
    reasons: list[str] = []
    warnings: list[str] = []

    score += _price_vs_vwap_score("NIFTY", nifty, reasons, warnings)
    score += _price_vs_vwap_score("BANKNIFTY", banknifty, reasons, warnings)

    if breadth.advance_pct >= 65:
        score += 2
        reasons.append(f"NIFTY universe breadth is strong: {breadth.advance_pct}% advancing")
    elif breadth.advance_pct >= 55:
        score += 1
        reasons.append(f"Breadth is mildly positive: {breadth.advance_pct}% advancing")
    elif breadth.advance_pct <= 35:
        score -= 2
        reasons.append(f"Breadth is weak: only {breadth.advance_pct}% advancing")
    elif breadth.advance_pct <= 45:
        score -= 1
        reasons.append(f"Breadth is mildly negative: {breadth.advance_pct}% advancing")
    else:
        warnings.append("Breadth is neutral; avoid forcing direction")

    score += _option_score("NIFTY", nifty_options, reasons, warnings)
    score += _option_score("BANKNIFTY", banknifty_options, reasons, warnings)

    score += global_context.score
    if global_context.score > 0:
        reasons.append("Global context is supportive")
    elif global_context.score < 0:
        warnings.append("Global context is risk-off")
    else:
        warnings.append("Global context is neutral")

    # Conflict penalty
    nifty_above = _above_vwap(nifty)
    bank_above = _above_vwap(banknifty)
    if nifty_above is not None and bank_above is not None and nifty_above != bank_above:
        score -= 1.5
        warnings.append("NIFTY and BANKNIFTY are not aligned")

    if score >= 6:
        bias = "bullish"
        action = "trade_only_on_trigger"
        confidence = "high"
    elif score >= 2:
        bias = "bullish_but_wait"
        action = "wait_for_confirmation"
        confidence = "medium"
    elif score <= -6:
        bias = "bearish"
        action = "trade_only_on_trigger"
        confidence = "high"
    elif score <= -2:
        bias = "bearish_but_wait"
        action = "wait_for_confirmation"
        confidence = "medium"
    else:
        bias = "range_bound"
        action = "avoid_or_scalp_only"
        confidence = "low"

    summary = f"{bias.replace('_', ' ').title()} | Score {round(score, 2)} | Action: {action.replace('_', ' ')}"

    return BiasResult(
        market_bias=bias,
        bias_score=round(score, 2),
        confidence=confidence,
        action=action,
        summary=summary,
        reasons=reasons,
        warnings=warnings,
    )


def _price_vs_vwap_score(name: str, quote: Quote, reasons: list[str], warnings: list[str]) -> float:
    if quote.vwap is None:
        warnings.append(f"{name} VWAP unavailable")
        return 0.0

    if quote.ltp > quote.vwap:
        reasons.append(f"{name} is above VWAP")
        return 1.5
    if quote.ltp < quote.vwap:
        reasons.append(f"{name} is below VWAP")
        return -1.5

    warnings.append(f"{name} is exactly near VWAP")
    return 0.0


def _option_score(name: str, chain: OptionChainAnalysis, reasons: list[str], warnings: list[str]) -> float:
    if chain.signal == "bullish":
        reasons.append(f"{name} option chain is bullish: " + "; ".join(chain.reason[:2]))
        warnings.extend([f"{name}: {x}" for x in chain.warning])
        return 1.5
    if chain.signal == "bearish":
        reasons.append(f"{name} option chain is bearish: " + "; ".join(chain.reason[:2]))
        warnings.extend([f"{name}: {x}" for x in chain.warning])
        return -1.5

    warnings.append(f"{name} option chain is neutral")
    return 0.0


def _above_vwap(quote: Quote) -> bool | None:
    if quote.vwap is None:
        return None
    return quote.ltp > quote.vwap
