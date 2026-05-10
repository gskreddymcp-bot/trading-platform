import asyncio
import sys
from pathlib import Path

# Allows: python jobs/run_once.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import SessionLocal, init_db
from app.services.scanner_service import run_full_scan


async def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = await run_full_scan(db)
        print(result.model_dump_json(indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
