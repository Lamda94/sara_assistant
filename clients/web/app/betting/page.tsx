"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { TrendingUp, Target, DollarSign, Activity, ChevronDown, ChevronUp } from "lucide-react";
import Sidebar from "@/components/Sidebar";

const BASE = "/api";

interface Bet {
  id: string;
  sport: string;
  event_name: string;
  event_date: string | null;
  league: string | null;
  market: string;
  selection: string;
  odds: number;
  stake_units: number;
  predicted_prob: number;
  implied_prob: number;
  edge: number;
  confidence: number;
  analysis_summary: string;
  result: string;
  profit_loss: number;
  post_mortem: string | null;
  created_at: string | null;
  resolved_at: string | null;
}

interface Metrics {
  model_status: string;
  total_bets: number;
  wins: number;
  losses: number;
  pending: number;
  win_rate: number;
  win_rate_last_5: number;
  roi: number;
  balance: number;
  total_profit: number;
  avg_edge: number;
  avg_confidence: number;
}

export default function BettingPage() {
  const { status } = useSession();
  const [bets, setBets] = useState<Bet[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    (async () => {
      setLoading(true);
      try {
        const [bRes, mRes] = await Promise.all([
          fetch(`${BASE}/betting/history?limit=20`),
          fetch(`${BASE}/betting/metrics`),
        ]);
        if (bRes.ok) setBets(await bRes.json());
        if (mRes.ok) setMetrics(await mRes.json());
      } finally {
        setLoading(false);
      }
    })();
  }, [status]);

  if (status === "loading" || loading) {
    return (
      <div style={{ display: "flex", height: "100vh", background: "#1A1C1E" }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ color: "#455A64", fontSize: 13 }}>Cargando SABE...</div>
        </div>
      </div>
    );
  }

  const statusColor = metrics?.model_status === "certified" ? "#4CAF50" : "#FF9800";
  const statusLabel = metrics?.model_status === "certified" ? "Certificado" : "Aprendizaje";

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#1A1C1E" }}>
      <Sidebar />
      <div style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#ECEFF1", margin: 0 }}>SABE</h1>
          <span style={{
            fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 6,
            background: `${statusColor}20`, color: statusColor, textTransform: "uppercase",
            letterSpacing: "0.05em",
          }}>
            {statusLabel}
          </span>
        </div>
        <p style={{ fontSize: 13, color: "#546E7A", margin: "0 0 32px" }}>
          Sistema de Analisis de Betting Estrategico
        </p>

        {/* Metrics Cards */}
        {metrics && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 32 }}>
            <MetricCard
              icon={<Target size={16} />}
              label="Win Rate (ult. 5)"
              value={`${metrics.win_rate_last_5}%`}
              color={metrics.win_rate_last_5 >= 85 ? "#4CAF50" : metrics.win_rate_last_5 >= 60 ? "#FF9800" : "#EF5350"}
            />
            <MetricCard
              icon={<TrendingUp size={16} />}
              label="Win Rate General"
              value={`${metrics.win_rate}%`}
              color="#78909C"
            />
            <MetricCard
              icon={<DollarSign size={16} />}
              label="Balance"
              value={`${metrics.balance.toFixed(0)}u`}
              sub={`ROI: ${metrics.roi > 0 ? "+" : ""}${metrics.roi}%`}
              color={metrics.roi >= 0 ? "#4CAF50" : "#EF5350"}
            />
            <MetricCard
              icon={<Activity size={16} />}
              label="Apuestas"
              value={`${metrics.total_bets}`}
              sub={`${metrics.wins}W ${metrics.losses}L ${metrics.pending}P`}
              color="#78909C"
            />
          </div>
        )}

        {/* Bets Table */}
        <h2 style={{ fontSize: 14, fontWeight: 600, color: "#78909C", marginBottom: 14, textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Historial de apuestas
        </h2>

        {bets.length === 0 ? (
          <div style={{ color: "#37474F", fontSize: 13, padding: "32px 0" }}>
            No hay apuestas simuladas registradas.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {bets.map(bet => {
              const isExpanded = expanded === bet.id;
              const resultIcon = bet.result === "win" ? "✅" : bet.result === "loss" ? "❌" : "⏳";
              const resultColor = bet.result === "win" ? "#4CAF50" : bet.result === "loss" ? "#EF5350" : "#FF9800";
              const pl = bet.profit_loss > 0 ? `+${bet.profit_loss.toFixed(1)}` : bet.profit_loss.toFixed(1);

              return (
                <div key={bet.id} style={{
                  background: "#1E2225",
                  borderRadius: 12,
                  border: `1px solid ${bet.result === "pending" ? "rgba(255,255,255,0.05)" : `${resultColor}25`}`,
                  overflow: "hidden",
                }}>
                  {/* Row */}
                  <div
                    onClick={() => setExpanded(isExpanded ? null : bet.id)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "14px 20px", cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
                      <span style={{ fontSize: 16 }}>{resultIcon}</span>
                      <div>
                        <p style={{ margin: 0, fontSize: 14, color: "#ECEFF1", fontWeight: 500 }}>
                          {bet.event_name}
                        </p>
                        <p style={{ margin: "3px 0 0", fontSize: 11, color: "#546E7A" }}>
                          {bet.league ?? bet.sport} — {bet.market.toUpperCase()} — {bet.selection}
                          {bet.event_date && (
                            <span style={{ color: "#455A64", marginLeft: 8 }}>
                              {new Date(bet.event_date).toLocaleDateString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
                      <div style={{ textAlign: "right" }}>
                        <p style={{ margin: 0, fontSize: 13, color: "#ECEFF1", fontWeight: 500 }}>
                          @{bet.odds.toFixed(2)}
                        </p>
                        <p style={{ margin: "2px 0 0", fontSize: 11, color: resultColor }}>
                          {bet.result !== "pending" ? `${pl}u` : "pendiente"}
                        </p>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{
                          fontSize: 11, padding: "3px 8px", borderRadius: 4,
                          background: `${resultColor}15`, color: resultColor,
                        }}>
                          {(bet.edge * 100).toFixed(1)}% edge
                        </span>
                        {isExpanded ? <ChevronUp size={14} color="#546E7A" /> : <ChevronDown size={14} color="#546E7A" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded */}
                  {isExpanded && (
                    <div style={{
                      padding: "0 20px 16px",
                      borderTop: "1px solid rgba(255,255,255,0.04)",
                    }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, padding: "14px 0" }}>
                        <MiniStat label="Prob. predicha" value={`${(bet.predicted_prob * 100).toFixed(0)}%`} />
                        <MiniStat label="Prob. implicita" value={`${(bet.implied_prob * 100).toFixed(0)}%`} />
                        <MiniStat label="Confianza" value={`${bet.confidence}%`} />
                        <MiniStat label="Stake" value={`${bet.stake_units.toFixed(1)}u`} />
                        <MiniStat label="Fecha evento" value={bet.event_date ? new Date(bet.event_date).toLocaleDateString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—"} />
                        <MiniStat label="Resultado" value={bet.result.toUpperCase()} />
                      </div>
                      {bet.analysis_summary && (
                        <div style={{ marginTop: 8 }}>
                          <p style={{ fontSize: 11, color: "#546E7A", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Analisis</p>
                          <p style={{ fontSize: 12, color: "#78909C", lineHeight: 1.5, margin: 0 }}>
                            {bet.analysis_summary}
                          </p>
                        </div>
                      )}
                      {bet.post_mortem && (
                        <div style={{ marginTop: 12, padding: "10px 12px", borderRadius: 8, background: "rgba(239,83,80,0.08)" }}>
                          <p style={{ fontSize: 11, color: "#EF5350", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>Post-mortem</p>
                          <p style={{ fontSize: 12, color: "#EF9A9A", lineHeight: 1.5, margin: 0 }}>
                            {bet.post_mortem}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value, sub, color }: {
  icon: React.ReactNode; label: string; value: string; sub?: string; color: string;
}) {
  return (
    <div style={{
      padding: "18px 20px", borderRadius: 12, background: "#1E2225",
      border: "1px solid rgba(255,255,255,0.05)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span style={{ color: "#546E7A" }}>{icon}</span>
        <span style={{ fontSize: 11, color: "#546E7A", textTransform: "uppercase", letterSpacing: "0.06em" }}>{label}</span>
      </div>
      <p style={{ fontSize: 24, fontWeight: 700, color, margin: 0 }}>{value}</p>
      {sub && <p style={{ fontSize: 11, color: "#546E7A", marginTop: 4, margin: "4px 0 0" }}>{sub}</p>}
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p style={{ fontSize: 10, color: "#455A64", textTransform: "uppercase", letterSpacing: "0.05em", margin: "0 0 3px" }}>{label}</p>
      <p style={{ fontSize: 13, color: "#ECEFF1", fontWeight: 500, margin: 0 }}>{value}</p>
    </div>
  );
}
