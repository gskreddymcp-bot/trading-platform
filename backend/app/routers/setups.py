from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import TradeSetup

router = APIRouter(prefix="/api/v1/setups", tags=["setups"])


@router.get("/latest")
def latest_setups(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(TradeSetup).order_by(TradeSetup.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "symbol": row.symbol,
            "direction": row.direction,
            "setup_type": row.setup_type,
            "entry": row.entry,
            "stop_loss": row.stop_loss,
            "target_1": row.target_1,
            "target_2": row.target_2,
            "risk_reward": row.risk_reward,
            "confidence": row.confidence,
            "decision": row.decision,
            "reason": row.reason,
            "invalidation": row.invalidation,
        }
        for row in rows
    ]
