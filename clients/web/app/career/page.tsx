"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { Briefcase, Search, FileText, TrendingUp, ChevronDown, ChevronUp, Power, Settings } from "lucide-react";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";

const BASE = "/api";
const SESSION_ID = "lamda94-web";

interface ScanResult {
  id: number;
  company: string;
  title: string;
  url: string;
  portal_source: string | null;
  first_seen_at: string | null;
}

interface Application {
  id: string;
  company: string;
  role: string;
  url: string | null;
  portal_source: string | null;
  score: number | null;
  compatibility_pct: number | null;
  archetype: string | null;
  evaluation_summary: string | null;
  evaluation_blocks: Record<string, string> | null;
  cv_path: string | null;
  legitimacy: string | null;
  status: string;
  applied_at: string | null;
  created_at: string | null;
}

interface Status {
  career_mode: boolean;
  total_applications: number;
  by_status: Record<string, number>;
  last_scan: { date: string | null; found: number; evaluated: number; cv_generated: number } | null;
}

export default function CareerPage() {
  const { status: authStatus } = useSession();
  const [apps, setApps] = useState<Application[]>([]);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [careerStatus, setCareerStatus] = useState<Status | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"found" | "evaluated">("found");

  const load = async () => {
    setLoading(true);
    try {
      const [sRes, aRes, srRes] = await Promise.all([
        fetch(`${BASE}/career/status?session_id=${SESSION_ID}`),
        fetch(`${BASE}/career/applications?limit=20`),
        fetch(`${BASE}/career/scan-results?limit=30`),
      ]);
      if (sRes.ok) setCareerStatus(await sRes.json());
      if (aRes.ok) setApps(await aRes.json());
      if (srRes.ok) setScanResults(await srRes.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (authStatus === "authenticated") load();
  }, [authStatus]);

  if (authStatus === "loading" || loading) {
    return (
      <div style={{ display: "flex", height: "100vh", background: "#1A1C1E" }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ color: "#455A64", fontSize: 13 }}>Cargando CareerOps...</div>
        </div>
      </div>
    );
  }

  const mode = careerStatus?.career_mode;
  const modeColor = mode ? "#4CAF50" : "#78909C";
  const byStatus = careerStatus?.by_status ?? {};
  const lastScan = careerStatus?.last_scan;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#1A1C1E" }}>
      <Sidebar />
      <div style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#ECEFF1", margin: 0 }}>CareerOps</h1>
          <span style={{
            fontSize: 11, fontWeight: 600, padding: "4px 10px", borderRadius: 6,
            background: `${modeColor}20`, color: modeColor, textTransform: "uppercase",
            letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: 4,
          }}>
            <Power size={10} />
            {mode ? "Activo" : "Inactivo"}
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
          <p style={{ fontSize: 13, color: "#546E7A", margin: 0 }}>
            Busqueda de empleo autonoma
          </p>
          <Link href="/career/setup" style={{
            display: "flex", alignItems: "center", gap: 6, padding: "8px 16px",
            borderRadius: 8, background: "#263238", border: "1px solid #455A64",
            color: "#ECEFF1", fontSize: 12, textDecoration: "none", fontWeight: 500,
          }}>
            <Settings size={14} /> Configurar
          </Link>
        </div>

        {/* Metrics */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 32 }}>
          <MetricCard
            icon={<Briefcase size={16} />}
            label="Evaluadas"
            value={`${careerStatus?.total_applications ?? 0}`}
            color="#78909C"
          />
          <MetricCard
            icon={<FileText size={16} />}
            label="CVs Generados"
            value={`${byStatus.cv_generated ?? 0}`}
            color="#42A5F5"
          />
          <MetricCard
            icon={<TrendingUp size={16} />}
            label="Aplicadas"
            value={`${byStatus.applied ?? 0}`}
            sub={`${byStatus.interview ?? 0} entrevistas`}
            color="#4CAF50"
          />
          <MetricCard
            icon={<Search size={16} />}
            label="Ultimo escaneo"
            value={lastScan?.date ? new Date(lastScan.date).toLocaleDateString("es", { day: "2-digit", month: "short" }) : "—"}
            sub={lastScan ? `${lastScan.found} encontradas` : "Sin escaneos"}
            color="#FF9800"
          />
        </div>

        {/* Status breakdown */}
        {Object.keys(byStatus).length > 0 && (
          <div style={{ display: "flex", gap: 8, marginBottom: 24, flexWrap: "wrap" }}>
            {Object.entries(byStatus).filter(([, v]) => v > 0).map(([status, count]) => (
              <span key={status} style={{
                fontSize: 11, padding: "4px 10px", borderRadius: 6,
                background: "rgba(255,255,255,0.04)", color: "#78909C",
              }}>
                {status}: {count}
              </span>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          {(["found", "evaluated"] as const).map(t => (
            <button key={t} onClick={() => setActiveTab(t)} style={{
              padding: "8px 18px", borderRadius: 9, cursor: "pointer",
              border: "1px solid", fontSize: 13,
              borderColor: activeTab === t ? "#455A64" : "rgba(255,255,255,0.06)",
              background: activeTab === t ? "#263238" : "transparent",
              color: activeTab === t ? "#ECEFF1" : "#546E7A",
            }}>
              {t === "found" ? `Encontradas (${scanResults.length})` : `Evaluadas (${apps.length})`}
            </button>
          ))}
        </div>

        {/* Scan Results */}
        {activeTab === "found" && (
          scanResults.length === 0 ? (
            <div style={{ color: "#37474F", fontSize: 13, padding: "32px 0" }}>
              No hay ofertas encontradas. Dile a SARA: "escanea portales"
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {scanResults.map(sr => (
                <div key={sr.id} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "12px 20px", borderRadius: 10, background: "#1E2225",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}>
                  <div style={{ flex: 1 }}>
                    <p style={{ margin: 0, fontSize: 14, color: "#ECEFF1", fontWeight: 500 }}>
                      {sr.company} — {sr.title}
                    </p>
                    <p style={{ margin: "3px 0 0", fontSize: 11, color: "#546E7A" }}>
                      {sr.first_seen_at && new Date(sr.first_seen_at).toLocaleDateString("es", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                  {sr.url && (
                    <a href={sr.url} target="_blank" rel="noopener noreferrer"
                      style={{ fontSize: 11, color: "#42A5F5", textDecoration: "none", flexShrink: 0, marginLeft: 12 }}>
                      Ver oferta →
                    </a>
                  )}
                </div>
              ))}
            </div>
          )
        )}

        {/* Applications */}
        {activeTab === "evaluated" && (apps.length === 0 ? (
          <div style={{ color: "#37474F", fontSize: 13, padding: "32px 0" }}>
            No hay evaluaciones. Dile a SARA: "evalua esta oferta: [url]"
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {apps.map(app => {
              const isExpanded = expanded === app.id;
              const score = app.score ?? 0;
              const scoreColor = score >= 4.5 ? "#4CAF50" : score >= 4.0 ? "#8BC34A" : score >= 3.5 ? "#FF9800" : "#EF5350";
              const statusIcon = {
                evaluated: "📋", cv_generated: "📄", applied: "✅",
                interview: "🎯", offer: "🏆", rejected: "❌", discarded: "🚫",
              }[app.status] ?? "📋";

              return (
                <div key={app.id} style={{
                  background: "#1E2225", borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.05)", overflow: "hidden",
                }}>
                  {/* Row */}
                  <div
                    onClick={() => setExpanded(isExpanded ? null : app.id)}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "14px 20px", cursor: "pointer",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1 }}>
                      <span style={{ fontSize: 16 }}>{statusIcon}</span>
                      <div>
                        <p style={{ margin: 0, fontSize: 14, color: "#ECEFF1", fontWeight: 500 }}>
                          {app.company} — {app.role}
                        </p>
                        <p style={{ margin: "3px 0 0", fontSize: 11, color: "#546E7A" }}>
                          {app.archetype ?? app.portal_source ?? "—"}
                          {app.created_at && (
                            <span style={{ marginLeft: 8, color: "#455A64" }}>
                              {new Date(app.created_at).toLocaleDateString("es", { day: "2-digit", month: "short" })}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                      <div style={{ textAlign: "right" }}>
                        <p style={{ margin: 0, fontSize: 16, fontWeight: 700, color: scoreColor }}>
                          {score > 0 ? `${score.toFixed(1)}` : "—"}<span style={{ fontSize: 11, fontWeight: 400 }}>/5</span>
                        </p>
                        {app.compatibility_pct != null && (
                          <p style={{ margin: "2px 0 0", fontSize: 11, color: "#546E7A" }}>
                            {app.compatibility_pct}% match
                          </p>
                        )}
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{
                          fontSize: 10, padding: "3px 8px", borderRadius: 4,
                          background: "rgba(255,255,255,0.05)", color: "#78909C",
                          textTransform: "uppercase",
                        }}>
                          {app.status.replace("_", " ")}
                        </span>
                        {app.cv_path && <FileText size={12} color="#42A5F5" />}
                        {isExpanded ? <ChevronUp size={14} color="#546E7A" /> : <ChevronDown size={14} color="#546E7A" />}
                      </div>
                    </div>
                  </div>

                  {/* Expanded detail */}
                  {isExpanded && (
                    <div style={{
                      padding: "0 20px 16px",
                      borderTop: "1px solid rgba(255,255,255,0.04)",
                    }}>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, padding: "14px 0" }}>
                        <MiniStat label="Score" value={score > 0 ? `${score.toFixed(1)}/5` : "—"} />
                        <MiniStat label="Compatibilidad" value={app.compatibility_pct != null ? `${app.compatibility_pct}%` : "—"} />
                        <MiniStat label="Legitimidad" value={app.legitimacy ?? "—"} />
                        <MiniStat label="Arquetipo" value={app.archetype ?? "—"} />
                        <MiniStat label="Estado" value={app.status.replace("_", " ").toUpperCase()} />
                        <MiniStat label="CV" value={app.cv_path ? "Generado" : "No"} />
                      </div>

                      {app.url && (
                        <div style={{ marginTop: 4 }}>
                          <a href={app.url} target="_blank" rel="noopener noreferrer"
                            style={{ fontSize: 12, color: "#42A5F5", textDecoration: "none" }}>
                            Ver oferta original →
                          </a>
                        </div>
                      )}

                      {app.evaluation_summary && (
                        <div style={{ marginTop: 12 }}>
                          <p style={{ fontSize: 11, color: "#546E7A", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Resumen de evaluacion
                          </p>
                          <p style={{ fontSize: 12, color: "#78909C", lineHeight: 1.6, margin: 0 }}>
                            {app.evaluation_summary}
                          </p>
                        </div>
                      )}

                      {app.evaluation_blocks && (
                        <div style={{ marginTop: 12 }}>
                          <p style={{ fontSize: 11, color: "#546E7A", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Bloques de evaluacion
                          </p>
                          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            {Object.entries(app.evaluation_blocks).map(([block, content]) => (
                              <div key={block} style={{
                                padding: "8px 12px", borderRadius: 8,
                                background: "rgba(255,255,255,0.03)",
                              }}>
                                <p style={{ fontSize: 11, color: "#78909C", fontWeight: 600, margin: "0 0 2px" }}>
                                  Bloque {block.toUpperCase()}
                                </p>
                                <p style={{ fontSize: 11, color: "#546E7A", margin: 0, lineHeight: 1.5 }}>
                                  {String(content).slice(0, 300)}
                                  {String(content).length > 300 ? "..." : ""}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}
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
