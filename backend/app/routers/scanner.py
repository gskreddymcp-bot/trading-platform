from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.scanner_service import run_full_scan, latest_scan_from_db

router = APIRouter(prefix="/api/v1/scanner", tags=["scanner"])


@router.post("/run")
async def run_scanner(db: Session = Depends(get_db)):
    return await run_full_scan(db)


@router.get("/latest")
async def latest_scan(db: Session = Depends(get_db)):
    latest = latest_scan_from_db(db)
    if latest is None:
        payload = await run_full_scan(db)
        latest = latest_scan_from_db(db)
        if latest is None:
            raise HTTPException(status_code=500, detail="Scanner did not persist result")
    return latest


@router.get("/history")
def scanner_history(limit: int = 20, db: Session = Depends(get_db)):
    from app.models import ScannerResult

    rows = db.query(ScannerResult).order_by(ScannerResult.id.desc()).limit(limit).all()
    return [
        {
            "id": x.id,
            "created_at": x.created_at,
            "market_bias": x.market_bias,
            "bias_score": x.bias_score,
            "confidence": x.confidence,
            "action": x.action,
            "summary": x.summary,
        }
        for x in rows
    ]
