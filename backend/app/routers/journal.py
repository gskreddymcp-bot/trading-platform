from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import JournalEntry, AuditLog
from app.schemas import JournalCreate

router = APIRouter(prefix="/api/v1/journal", tags=["journal"])


@router.post("")
def create_journal(entry: JournalCreate, db: Session = Depends(get_db)):
    row = JournalEntry(
        setup_id=entry.setup_id,
        symbol=entry.symbol,
        action=entry.action,
        notes=entry.notes,
        outcome=entry.outcome,
        payload=entry.payload,
    )
    db.add(row)
    db.add(
        AuditLog(
            event_type="journal.create",
            message=f"{entry.symbol}: {entry.action}",
            payload=entry.model_dump(mode="json"),
        )
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "created_at": row.created_at,
        "setup_id": row.setup_id,
        "symbol": row.symbol,
        "action": row.action,
        "notes": row.notes,
        "outcome": row.outcome,
        "payload": row.payload,
    }


@router.get("")
def list_journal(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(JournalEntry).order_by(JournalEntry.id.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "created_at": row.created_at,
            "setup_id": row.setup_id,
            "symbol": row.symbol,
            "action": row.action,
            "notes": row.notes,
            "outcome": row.outcome,
            "payload": row.payload,
        }
        for row in rows
    ]
