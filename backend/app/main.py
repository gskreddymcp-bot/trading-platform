from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.db import init_db
from app.routers.health import router as health_router
from app.routers.market import router as market_router
from app.routers.options import router as options_router
from app.routers.scanner import router as scanner_router
from app.routers.setups import router as setups_router
from app.routers.journal import router as journal_router


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Indian Market Intelligence + Options Decision Support OS V1. No live order execution.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(health_router)
app.include_router(market_router)
app.include_router(options_router)
app.include_router(scanner_router)
app.include_router(setups_router)
app.include_router(journal_router)
