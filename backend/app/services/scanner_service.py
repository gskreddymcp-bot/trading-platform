from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    MarketSnapshot,
    OptionChainSnapshot,
    ScannerResult,
    TradeSetup,
    AuditLog,
)
from app.providers import get_market_provider
from app.schemas import ScannerPayload
from .instrument_service import load_top_instruments
from .breadth_service import calculate_breadth
from .option_chain_service import analyze_option_chain
from .global_context_service import parse_global_context
from .bias_engine import calculate_market_bias
from .setup_engine import generate_setups


async def run_full_scan(db: Session) -> ScannerPayload:
    settings = get_settings()
    provider = get_market_provider()

    instruments = load_top_instruments(settings.scan_top_stock_limit)
    top_keys = [x.instrument_key for x in instruments]

    index_keys = [
        settings.nifty_index_key,
        settings.banknifty_index_key,
    ]

    index_quotes = await provider.get_quotes(index_keys)
    index_quote_by_key = {q.instrument_key: q for q in index_quotes}

    nifty = index_quote_by_key.get(settings.nifty_index_key)
    banknifty = index_quote_by_key.get(settings.banknifty_index_key)

    if nifty is None or banknifty is None:
        raise RuntimeError(
            "Could not load NIFTY and BANKNIFTY quotes. "
            f"requested={index_keys}, returned={list(index_quote_by_key.keys())}"
        )

    top_quotes = []

    if top_keys:
        try:
            top_quotes = await provider.get_quotes(top_keys)
        except Exception as exc:
            db.add(
                AuditLog(
                    event_type="scanner.top_quotes.warning",
                    message="Top-stock quote scan failed; continuing with index scan",
                    payload={"error": str(exc)},
                )
            )
            db.commit()
            top_quotes = []

    breadth = calculate_breadth(top_quotes, instruments)

    nifty_expiry = settings.default_nifty_expiry
    banknifty_expiry = settings.default_banknifty_expiry

    if hasattr(provider, "resolve_option_expiry"):
        resolved_nifty_expiry = await provider.resolve_option_expiry(
            settings.nifty_index_key,
            settings.default_nifty_expiry,
        )

        resolved_banknifty_expiry = await provider.resolve_option_expiry(
            settings.banknifty_index_key,
            settings.default_banknifty_expiry,
        )

        if resolved_nifty_expiry != settings.default_nifty_expiry:
            db.add(
                AuditLog(
                    event_type="scanner.expiry.autoresolved",
                    message="NIFTY expiry auto-resolved",
                    payload={
                        "configured": settings.default_nifty_expiry,
                        "resolved": resolved_nifty_expiry,
                    },
                )
            )

        if resolved_banknifty_expiry != settings.default_banknifty_expiry:
            db.add(
                AuditLog(
                    event_type="scanner.expiry.autoresolved",
                    message="BANKNIFTY expiry auto-resolved",
                    payload={
                        "configured": settings.default_banknifty_expiry,
                        "resolved": resolved_banknifty_expiry,
                    },
                )
            )

        db.commit()

        nifty_expiry = resolved_nifty_expiry
        banknifty_expiry = resolved_banknifty_expiry

    nifty_spot, nifty_levels = await provider.get_option_chain(
        settings.nifty_index_key,
        nifty_expiry,
    )

    bank_spot, bank_levels = await provider.get_option_chain(
        settings.banknifty_index_key,
        banknifty_expiry,
    )

    nifty_options = analyze_option_chain(
        "NIFTY",
        nifty_expiry,
        nifty_spot,
        nifty_levels,
    )

    banknifty_options = analyze_option_chain(
        "BANKNIFTY",
        banknifty_expiry,
        bank_spot,
        bank_levels,
    )

    global_context = parse_global_context(await provider.get_global_context())

    bias = calculate_market_bias(
        nifty=nifty,
        banknifty=banknifty,
        breadth=breadth,
        nifty_options=nifty_options,
        banknifty_options=banknifty_options,
        global_context=global_context,
    )

    setups = generate_setups(
        bias=bias,
        nifty=nifty,
        banknifty=banknifty,
        nifty_options=nifty_options,
        banknifty_options=banknifty_options,
    )

    payload = ScannerPayload(
        bias=bias,
        nifty=nifty,
        banknifty=banknifty,
        breadth=breadth,
        nifty_options=nifty_options,
        banknifty_options=banknifty_options,
        global_context=global_context,
        setups=setups,
    )

    _persist_scan(db, payload)

    return payload


def _persist_scan(db: Session, payload: ScannerPayload) -> None:
    for q in [payload.nifty, payload.banknifty]:
        db.add(
            MarketSnapshot(
                symbol=q.symbol,
                instrument_key=q.instrument_key,
                ltp=q.ltp,
                open=q.open,
                high=q.high,
                low=q.low,
                close=q.close,
                volume=q.volume,
                vwap=q.vwap,
                raw=q.raw,
            )
        )

    for chain in [payload.nifty_options, payload.banknifty_options]:
        db.add(
            OptionChainSnapshot(
                symbol=chain.symbol,
                expiry=chain.expiry,
                spot_price=chain.spot_price,
                atm_strike=chain.atm_strike,
                pcr=chain.pcr,
                max_pain=chain.max_pain,
                support_zones=chain.support_zones,
                resistance_zones=chain.resistance_zones,
                signal=chain.signal,
                reason=chain.reason,
                warning=chain.warning,
                raw={
                    "levels": [
                        x.model_dump()
                        for x in chain.levels
                    ]
                },
            )
        )

    result = ScannerResult(
        market_bias=payload.bias.market_bias,
        bias_score=payload.bias.bias_score,
        confidence=payload.bias.confidence,
        action=payload.bias.action,
        summary=payload.bias.summary,
        reasons=payload.bias.reasons,
        warnings=payload.bias.warnings,
        payload=payload.model_dump(mode="json"),
    )

    db.add(result)
    db.flush()

    for setup in payload.setups:
        db.add(
            TradeSetup(
                scanner_result_id=result.id,
                symbol=setup.symbol,
                direction=setup.direction,
                setup_type=setup.setup_type,
                entry=setup.entry,
                stop_loss=setup.stop_loss,
                target_1=setup.target_1,
                target_2=setup.target_2,
                risk_reward=setup.risk_reward,
                confidence=setup.confidence,
                decision=setup.decision,
                reason=setup.reason,
                invalidation=setup.invalidation,
            )
        )

    db.add(
        AuditLog(
            event_type="scanner.run",
            message=payload.bias.summary,
            payload={
                "bias": payload.bias.model_dump(mode="json"),
                "nifty": payload.nifty.model_dump(mode="json"),
                "banknifty": payload.banknifty.model_dump(mode="json"),
                "nifty_expiry": payload.nifty_options.expiry,
                "banknifty_expiry": payload.banknifty_options.expiry,
                "nifty_options_signal": payload.nifty_options.signal,
                "banknifty_options_signal": payload.banknifty_options.signal,
            },
        )
    )

    db.commit()


def latest_scan_from_db(db: Session) -> dict | None:
    result = db.query(ScannerResult).order_by(ScannerResult.id.desc()).first()

    if not result:
        return None

    return {
        "id": result.id,
        "created_at": result.created_at,
        "market_bias": result.market_bias,
        "bias_score": result.bias_score,
        "confidence": result.confidence,
        "action": result.action,
        "summary": result.summary,
        "reasons": result.reasons,
        "warnings": result.warnings,
        "payload": result.payload,
    }