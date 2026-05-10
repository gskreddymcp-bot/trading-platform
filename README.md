# Market Intelligence OS V1

Market Intelligence OS V1 is a local-first Indian market decision-support system.

It scans:

- NIFTY
- BANKNIFTY
- configurable NIFTY 100 / top-stock universe
- NIFTY and BANKNIFTY option chains
- global market context
- news risk placeholders
- setup candidates
- risk decisions
- journal entries

V1 deliberately **does not place live orders**.

The system runs in two modes:

| Mode | Purpose |
|---|---|
| `mock` | Runs immediately with synthetic market data |
| `upstox` | Uses Upstox REST APIs for quotes and option chain |

## Quick start - local backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Run one scanner cycle from CLI:

```bash
cd backend
python jobs/run_once.py
```

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/scanner/latest
```

## Quick start - frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Docker compose

```bash
cp .env.example .env
docker compose up --build
```

Backend:

```text
http://127.0.0.1:8000
```

Frontend:

```text
http://127.0.0.1:5173
```

## Enable Upstox mode

Edit `.env`:

```env
DATA_PROVIDER=upstox
UPSTOX_ACCESS_TOKEN=your_token_here
```

For V1, start with these real instrument keys:

```env
NIFTY_INDEX_KEY=NSE_INDEX|Nifty 50
BANKNIFTY_INDEX_KEY=NSE_INDEX|Nifty Bank
```

Top stock keys are loaded from:

```text
data/instruments_top100.csv
```

Replace placeholders with real Upstox `instrument_key` values.

## Main endpoints

```text
GET  /health
GET  /api/v1/market/summary
GET  /api/v1/options/nifty
GET  /api/v1/options/banknifty
POST /api/v1/scanner/run
GET  /api/v1/scanner/latest
GET  /api/v1/setups/latest
POST /api/v1/journal
GET  /api/v1/journal
```

## V1 design rule

AI can summarize and explain.  
The deterministic scanner/risk engine decides `trade`, `wait`, or `avoid`.

No live broker execution exists in V1 by design.
# trading-platform
