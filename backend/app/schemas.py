from datetime import datetime
from pydantic import BaseModel, Field


class Quote(BaseModel):
    symbol: str
    instrument_key: str
    ltp: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    vwap: float | None = None
    raw: dict = Field(default_factory=dict)


class BreadthSummary(BaseModel):
    advancing: int
    declining: int
    unchanged: int
    total: int
    advance_pct: float
    leading_sectors: list[str] = Field(default_factory=list)
    weak_sectors: list[str] = Field(default_factory=list)


class OptionChainLevel(BaseModel):
    strike: float
    call_oi: float = 0
    put_oi: float = 0
    call_prev_oi: float = 0
    put_prev_oi: float = 0
    call_change_oi: float = 0
    put_change_oi: float = 0
    call_volume: float = 0
    put_volume: float = 0
    call_iv: float | None = None
    put_iv: float | None = None
    call_ltp: float | None = None
    put_ltp: float | None = None


class OptionChainAnalysis(BaseModel):
    symbol: str
    expiry: str
    spot_price: float
    atm_strike: float
    pcr: float
    max_pain: float | None = None
    support_zones: list[float] = Field(default_factory=list)
    resistance_zones: list[float] = Field(default_factory=list)
    signal: str = "neutral"
    reason: list[str] = Field(default_factory=list)
    warning: list[str] = Field(default_factory=list)
    levels: list[OptionChainLevel] = Field(default_factory=list)


class GlobalContext(BaseModel):
    global_risk_mood: str
    score: float
    drivers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class BiasResult(BaseModel):
    market_bias: str
    bias_score: float
    confidence: str
    action: str
    summary: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TradeSetupOut(BaseModel):
    id: int | None = None
    symbol: str
    direction: str
    setup_type: str
    entry: float | None = None
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    risk_reward: float | None = None
    confidence: str
    decision: str
    reason: list[str] = Field(default_factory=list)
    invalidation: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class ScannerPayload(BaseModel):
    bias: BiasResult
    nifty: Quote
    banknifty: Quote
    breadth: BreadthSummary
    nifty_options: OptionChainAnalysis
    banknifty_options: OptionChainAnalysis
    global_context: GlobalContext
    setups: list[TradeSetupOut] = Field(default_factory=list)


class JournalCreate(BaseModel):
    setup_id: int | None = None
    symbol: str
    action: str
    notes: str
    outcome: str | None = None
    payload: dict = Field(default_factory=dict)


class JournalOut(JournalCreate):
    id: int
    created_at: datetime
