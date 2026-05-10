from app.schemas import GlobalContext


def parse_global_context(raw: dict) -> GlobalContext:
    return GlobalContext(
        global_risk_mood=raw.get("global_risk_mood", "neutral"),
        score=float(raw.get("score", 0)),
        drivers=list(raw.get("drivers", [])),
        warnings=list(raw.get("warnings", [])),
    )
