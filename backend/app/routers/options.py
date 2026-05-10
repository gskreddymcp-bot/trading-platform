from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.scanner_service import latest_scan_from_db, run_full_scan

router = APIRouter(prefix="/api/v1/options", tags=["options"])


@router.get("/nifty")
async def nifty_options(db: Session = Depends(get_db)):
    latest = latest_scan_from_db(db)
    if latest is None:
        await run_full_scan(db)
        latest = latest_scan_from_db(db)
    return latest["payload"]["nifty_options"]


@router.get("/banknifty")
async def banknifty_options(db: Session = Depends(get_db)):
    latest = latest_scan_from_db(db)
    if latest is None:
        await run_full_scan(db)
        latest = latest_scan_from_db(db)
    return latest["payload"]["banknifty_options"]
