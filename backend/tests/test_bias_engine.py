from app.schemas import Quote, BreadthSummary, OptionChainAnalysis, GlobalContext
from app.services.bias_engine import calculate_market_bias


def test_bias_engine_bullish_case():
    nifty = Quote(symbol="NIFTY", instrument_key="nifty", ltp=101, vwap=100)
    bank = Quote(symbol="BANKNIFTY", instrument_key="bank", ltp=201, vwap=200)
    breadth = BreadthSummary(advancing=70, declining=30, unchanged=0, total=100, advance_pct=70)
    opt = OptionChainAnalysis(
        symbol="NIFTY",
        expiry="2026-05-28",
        spot_price=101,
        atm_strike=100,
        pcr=1.1,
        signal="bullish",
        reason=["put writing"],
    )
    g = GlobalContext(global_risk_mood="risk_on", score=1, drivers=["positive"], warnings=[])

    result = calculate_market_bias(nifty, bank, breadth, opt, opt, g)
    assert "bullish" in result.market_bias
    assert result.bias_score > 0
