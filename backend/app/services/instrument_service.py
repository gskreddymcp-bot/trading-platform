import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Instrument:
    instrument_key: str
    symbol: str
    sector: str


def load_top_instruments(limit: int = 100) -> list[Instrument]:
    candidates = [
        Path("data/instruments_top100.csv"),
        Path("../data/instruments_top100.csv"),
        Path("/app/data/instruments_top100.csv"),
    ]

    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return []

    out: list[Instrument] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            out.append(
                Instrument(
                    instrument_key=row["instrument_key"],
                    symbol=row["symbol"],
                    sector=row.get("sector", "Unknown"),
                )
            )
            if len(out) >= limit:
                break
    return out
