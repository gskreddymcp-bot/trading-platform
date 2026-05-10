import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { RefreshCw, AlertTriangle, TrendingUp, BarChart3 } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function Card({ title, children, icon }) {
  return (
    <section className="card">
      <div className="card-title">
        {icon}
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Badge({ children, tone = "neutral" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

function App() {
  const [scan, setScan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadLatest() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/scanner/latest`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const json = await res.json();
      setScan(json);
    } catch (err) {
      setError(err.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  async function runScan() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/v1/scanner/run`, { method: "POST" });
      if (!res.ok) throw new Error(`API error ${res.status}`);
      await loadLatest();
    } catch (err) {
      setError(err.message || "Failed to run scan");
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLatest();
  }, []);

  const payload = scan?.payload;
  const bias = payload?.bias;

  return (
    <main className="page">
      <header className="header">
        <div>
          <h1>Market Intelligence OS V1</h1>
          <p>NIFTY • BANKNIFTY • Option Chain • Breadth • Setup Engine</p>
        </div>
        <button onClick={runScan} disabled={loading}>
          <RefreshCw size={18} />
          {loading ? "Scanning..." : "Run Scan"}
        </button>
      </header>

      {error && <div className="error">{error}</div>}

      {!payload ? (
        <div className="loading">Loading scanner...</div>
      ) : (
        <>
          <Card title="Command Center" icon={<BarChart3 size={22} />}>
            <div className="command">
              <div>
                <div className="label">Bias</div>
                <div className="big">{bias.market_bias.replaceAll("_", " ")}</div>
              </div>
              <div>
                <div className="label">Score</div>
                <div className="big">{bias.bias_score}</div>
              </div>
              <div>
                <div className="label">Action</div>
                <Badge tone={bias.action.includes("trade") ? "green" : "yellow"}>
                  {bias.action.replaceAll("_", " ")}
                </Badge>
              </div>
              <div>
                <div className="label">Confidence</div>
                <Badge>{bias.confidence}</Badge>
              </div>
            </div>
            <p className="summary">{bias.summary}</p>
          </Card>

          <div className="grid two">
            <Card title="NIFTY / BANKNIFTY" icon={<TrendingUp size={22} />}>
              <IndexRow q={payload.nifty} />
              <IndexRow q={payload.banknifty} />
              <div className="mini">
                <b>Breadth:</b> {payload.breadth.advancing} advancing / {payload.breadth.declining} declining ({payload.breadth.advance_pct}%)
              </div>
              <div className="mini">
                <b>Leaders:</b> {payload.breadth.leading_sectors.join(", ") || "NA"}
              </div>
              <div className="mini">
                <b>Weak:</b> {payload.breadth.weak_sectors.join(", ") || "NA"}
              </div>
            </Card>

            <Card title="Global Context" icon={<AlertTriangle size={22} />}>
              <div className="big">{payload.global_context.global_risk_mood.replaceAll("_", " ")}</div>
              <ul>
                {payload.global_context.drivers.map((x, idx) => <li key={idx}>{x}</li>)}
              </ul>
              {payload.global_context.warnings?.length > 0 && (
                <div className="warn">
                  {payload.global_context.warnings.map((x, idx) => <div key={idx}>{x}</div>)}
                </div>
              )}
            </Card>
          </div>

          <div className="grid two">
            <OptionCard title="NIFTY Option Chain" chain={payload.nifty_options} />
            <OptionCard title="BANKNIFTY Option Chain" chain={payload.banknifty_options} />
          </div>

          <Card title="Setup Candidates" icon={<TrendingUp size={22} />}>
            <div className="setups">
              {payload.setups.map((s, idx) => (
                <div className="setup" key={idx}>
                  <div className="setup-head">
                    <b>{s.symbol}</b>
                    <Badge tone={s.decision.includes("trade") ? "green" : s.decision === "reject" ? "red" : "yellow"}>
                      {s.decision.replaceAll("_", " ")}
                    </Badge>
                  </div>
                  <div>{s.setup_type.replaceAll("_", " ")} • {s.direction}</div>
                  <div className="levels">
                    Entry: {s.entry ?? "-"} | SL: {s.stop_loss ?? "-"} | T1: {s.target_1 ?? "-"} | RR: {s.risk_reward ?? "-"}
                  </div>
                  <ul>
                    {s.reason.slice(0, 3).map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Reasons & Warnings" icon={<AlertTriangle size={22} />}>
            <div className="grid two">
              <div>
                <h3>Reasons</h3>
                <ul>{bias.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
              <div>
                <h3>Warnings</h3>
                <ul>{bias.warnings.map((x, i) => <li key={i}>{x}</li>)}</ul>
              </div>
            </div>
          </Card>
        </>
      )}
    </main>
  );
}

function IndexRow({ q }) {
  const above = q.vwap ? q.ltp > q.vwap : null;
  return (
    <div className="index-row">
      <div>
        <b>{q.symbol}</b>
        <div className="muted">{q.instrument_key}</div>
      </div>
      <div className="right">
        <div className="price">{q.ltp}</div>
        <Badge tone={above ? "green" : "red"}>{above ? "above VWAP" : "below VWAP"}</Badge>
      </div>
    </div>
  );
}

function OptionCard({ title, chain }) {
  return (
    <Card title={title} icon={<BarChart3 size={22} />}>
      <div className="command small">
        <div><div className="label">Spot</div><div className="big">{chain.spot_price}</div></div>
        <div><div className="label">ATM</div><div className="big">{chain.atm_strike}</div></div>
        <div><div className="label">PCR</div><div className="big">{chain.pcr}</div></div>
        <div><div className="label">Signal</div><Badge tone={chain.signal === "bullish" ? "green" : chain.signal === "bearish" ? "red" : "yellow"}>{chain.signal}</Badge></div>
      </div>
      <div className="mini"><b>Support:</b> {chain.support_zones.join(", ") || "NA"}</div>
      <div className="mini"><b>Resistance:</b> {chain.resistance_zones.join(", ") || "NA"}</div>
      <ul>{chain.reason.slice(0, 3).map((x, i) => <li key={i}>{x}</li>)}</ul>
    </Card>
  );
}

createRoot(document.getElementById("root")).render(<App />);
