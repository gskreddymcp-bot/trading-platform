from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.scanner_service import latest_scan_from_db, run_full_scan

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/summary")
async def market_summary(db: Session = Depends(get_db)):
    latest = latest_scan_from_db(db)
    if latest is None:
        await run_full_scan(db)
        latest = latest_scan_from_db(db)
    payload = latest["payload"]
    return {
        "bias": payload["bias"],
        "nifty": payload["nifty"],
        "banknifty": payload["banknifty"],
        "breadth": payload["breadth"],
        "global_context": payload["global_context"],
    }


@router.get("/top100/breadth")
async def top100_breadth(db: Session = Depends(get_db)):
    latest = latest_scan_from_db(db)
    if latest is None:
        await run_full_scan(db)
        latest = latest_scan_from_db(db)
    return latest["payload"]["breadth"]
