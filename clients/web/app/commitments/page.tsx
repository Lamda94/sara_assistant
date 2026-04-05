"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { ClipboardCheck, X, Search, Bell, Clock, AlertTriangle, User } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { getInsights, getAllInsights, dismissInsight, type Insight } from "@/lib/api";

const SESSION_ID = "lamda94-web";

type Filter = "all" | "overdue" | "pending" | "notified";

function dueBadge(dueDate: string | null): { label: string; color: string } {
  if (!dueDate) return { label: "sin fecha", color: "#455A64" };
  const now = new Date();
  const due = new Date(dueDate);
  const diffMs = due.getTime() - new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays < 0) return { label: "vencido", color: "#B71C1C" };
  if (diffDays === 0) return { label: "hoy", color: "#E65100" };
  if (diffDays === 1) return { label: "mañana", color: "#F57F17" };
  return { label: due.toLocaleDateString("es", { day: "2-digit", month: "short" }), color: "#455A64" };
}

function matchesFilter(ins: Insight, filter: Filter): boolean {
  if (filter === "all") return true;
  if (filter === "notified") return ins.notified;
  if (filter === "overdue") {
    if (!ins.due_date) return false;
    return new Date(ins.due_date) < new Date(new Date().toDateString());
  }
  // pending = not notified
  return !ins.notified;
}

function InsightCard({ ins, onDismiss }: { ins: Insight; onDismiss: (id: string) => void }) {
  const badge = dueBadge(ins.due_date);
  return (
    <div style={{
      borderRadius: 12, padding: "16px 20px",
      background: "#1E2427", border: "1px solid rgba(255,255,255,0.05)",
      display: "flex", alignItems: "flex-start", gap: 14,
    }}>
      {/* Indicator */}
      <div style={{
        width: 6, height: 6, borderRadius: "50%",
        background: badge.color, flexShrink: 0, marginTop: 7,
      }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 14, lineHeight: 1.6, color: "#B0BEC5", margin: 0 }}>
          {ins.content}
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
          {/* Due badge */}
          <span style={{
            fontSize: 11, padding: "2px 8px", borderRadius: 6,
            background: `${badge.color}22`, color: badge.color,
            fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.04em",
          }}>
            {badge.label}
          </span>
          {/* Type badge */}
          <span style={{
            fontSize: 11, padding: "2px 8px", borderRadius: 6,
            background: "rgba(69,90,100,0.2)", color: "#78909C",
            letterSpacing: "0.04em",
          }}>
            {ins.type}
          </span>
          {/* Notified indicator */}
          {ins.notified && (
            <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, color: "#455A64" }}>
              <Bell size={11} strokeWidth={1.8} /> notificado
            </span>
          )}
          {/* Date */}
          {ins.created_at && (
            <span style={{ fontSize: 11, color: "#37474F" }}>
              {new Date(ins.created_at).toLocaleDateString("es", { day: "2-digit", month: "short" })}
            </span>
          )}
        </div>
      </div>

      {/* Dismiss */}
      <button
        onClick={() => onDismiss(ins.id)}
        title="Descartar"
        style={{
          background: "none", border: "none", cursor: "pointer", color: "#37474F",
          padding: 4, flexShrink: 0, borderRadius: 6,
        }}
        onMouseEnter={e => (e.currentTarget.style.color = "#B71C1C")}
        onMouseLeave={e => (e.currentTarget.style.color = "#37474F")}
      >
        <X size={14} strokeWidth={1.8} />
      </button>
    </div>
  );
}

const FILTERS: { key: Filter; label: string; icon: typeof Clock }[] = [
  { key: "all",      label: "Todos",       icon: ClipboardCheck },
  { key: "overdue",  label: "Vencidos",    icon: AlertTriangle },
  { key: "pending",  label: "Pendientes",  icon: Clock },
  { key: "notified", label: "Notificados", icon: Bell },
];

export default function CommitmentsPage() {
  const { data: session } = useSession();
  const user = session?.user as any;
  const isCreator = user?.isCreator ?? false;

  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const load = isCreator ? getAllInsights : () => getInsights(SESSION_ID);
    load()
      .then(setInsights)
      .catch(() => setInsights([]))
      .finally(() => setLoading(false));
  }, [isCreator]);

  const handleDismiss = async (id: string) => {
    await dismissInsight(id);
    setInsights(prev => prev.filter(i => i.id !== id));
  };

  // Apply filters
  const filtered = insights
    .filter(i => matchesFilter(i, filter))
    .filter(i => !search.trim() || i.content.toLowerCase().includes(search.toLowerCase()));

  // Group by user for creator view
  const grouped: Record<string, Insight[]> = {};
  if (isCreator) {
    for (const ins of filtered) {
      const sid = ins.session_id ?? "desconocido";
      if (!grouped[sid]) grouped[sid] = [];
      grouped[sid].push(ins);
    }
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0, background: "#1A1C1E" }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "22px 40px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          flexShrink: 0,
        }}>
          <ClipboardCheck size={20} strokeWidth={1.8} color="#78909C" />
          <div>
            <p style={{ fontSize: 16, fontWeight: 600, color: "#ECEFF1", margin: 0 }}>Compromisos</p>
            <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#455A64", marginTop: 4 }}>
              {filtered.length} compromiso{filtered.length !== 1 ? "s" : ""}
              {isCreator ? " (todos los usuarios)" : ""}
            </p>
          </div>
        </div>

        {/* Search + Filters */}
        <div style={{
          padding: "20px 40px", borderBottom: "1px solid rgba(255,255,255,0.04)",
          flexShrink: 0, display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap",
        }}>
          {/* Search */}
          <div style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: "11px 18px", borderRadius: 10, flex: "1 1 280px", maxWidth: 400,
            background: "#1E2427", border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <Search size={14} strokeWidth={1.8} color="#455A64" />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Buscar compromisos..."
              style={{
                flex: 1, background: "transparent", border: "none", outline: "none",
                fontSize: 13, color: "#ECEFF1", fontFamily: "inherit",
              }} />
          </div>

          {/* Filter pills */}
          <div style={{ display: "flex", gap: 6 }}>
            {FILTERS.map(f => {
              const active = filter === f.key;
              return (
                <button key={f.key} onClick={() => setFilter(f.key)} style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "7px 14px", borderRadius: 8, border: "none", cursor: "pointer",
                  fontSize: 11, fontWeight: 500, fontFamily: "inherit",
                  letterSpacing: "0.04em", textTransform: "uppercase",
                  background: active ? "rgba(69,90,100,0.3)" : "rgba(255,255,255,0.03)",
                  color: active ? "#ECEFF1" : "#455A64",
                  transition: "all 0.15s",
                }}>
                  <f.icon size={12} strokeWidth={1.8} />
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "28px 40px" }}>
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 160 }}>
              <span style={{ fontSize: 14, color: "#455A64" }}>Cargando compromisos...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 160, gap: 12 }}>
              <ClipboardCheck size={32} strokeWidth={1.3} color="#263238" />
              <span style={{ fontSize: 14, color: "#455A64" }}>
                {search ? "Sin resultados para esa búsqueda" : "No hay compromisos registrados"}
              </span>
            </div>
          ) : isCreator ? (
            /* Creator: grouped by user */
            <div style={{ display: "grid", gap: 28, maxWidth: 720 }}>
              {Object.entries(grouped).map(([sid, items]) => (
                <div key={sid}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                    <User size={14} strokeWidth={1.8} color="#455A64" />
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#78909C", letterSpacing: "0.02em" }}>
                      {sid}
                    </span>
                    <span style={{
                      fontSize: 11, color: "#37474F", background: "rgba(255,255,255,0.04)",
                      padding: "2px 8px", borderRadius: 6,
                    }}>
                      {items.length}
                    </span>
                  </div>
                  <div style={{ display: "grid", gap: 10 }}>
                    {items.map(ins => <InsightCard key={ins.id} ins={ins} onDismiss={handleDismiss} />)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Normal user: flat list */
            <div style={{ display: "grid", gap: 10, maxWidth: 680 }}>
              {filtered.map(ins => <InsightCard key={ins.id} ins={ins} onDismiss={handleDismiss} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
