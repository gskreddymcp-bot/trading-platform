from collections import defaultdict
from app.schemas import Quote, BreadthSummary
from .instrument_service import Instrument


def calculate_breadth(quotes: list[Quote], instruments: list[Instrument]) -> BreadthSummary:
    sector_by_key = {x.instrument_key: x.sector for x in instruments}
    sector_scores: dict[str, list[float]] = defaultdict(list)

    advancing = declining = unchanged = 0

    for q in quotes:
        ref = q.close if q.close else q.open
        if not ref:
            unchanged += 1
            continue

        pct = ((q.ltp - ref) / ref) * 100
        sector_scores[sector_by_key.get(q.instrument_key, "Unknown")].append(pct)

        if pct > 0.05:
            advancing += 1
        elif pct < -0.05:
            declining += 1
        else:
            unchanged += 1

    total = max(1, advancing + declining + unchanged)
    sector_avg = {
        sector: sum(values) / len(values)
        for sector, values in sector_scores.items()
        if values
    }

    leading = [k for k, _ in sorted(sector_avg.items(), key=lambda item: item[1], reverse=True)[:3]]
    weak = [k for k, _ in sorted(sector_avg.items(), key=lambda item: item[1])[:3]]

    return BreadthSummary(
        advancing=advancing,
        declining=declining,
        unchanged=unchanged,
        total=total,
        advance_pct=round((advancing / total) * 100, 2),
        leading_sectors=leading,
        weak_sectors=weak,
    )
