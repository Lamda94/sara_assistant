"use client";
import { useState, useEffect } from "react";
import { Search, Brain } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { getMemories, searchMemories, type Memory } from "@/lib/api";

function MemoryCard({ mem }: { mem: Memory }) {
  return (
    <div style={{
      borderRadius: 12, padding: "18px 22px",
      background: "#1E2427", border: "1px solid rgba(255,255,255,0.05)",
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
        <div style={{
          width: 5, height: 5, borderRadius: "50%", background: "#455A64",
          flexShrink: 0, marginTop: 8,
        }} />
        <p style={{ fontSize: 14, lineHeight: 1.7, color: "#B0BEC5", margin: 0 }}>{mem.content}</p>
      </div>
    </div>
  );
}

export default function MemoryPage() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMemories().then(d => { setMemories(d.memories); setTotal(d.total); setLoading(false); });
  }, []);

  const handleSearch = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    if (!q.trim()) {
      const d = await getMemories(); setMemories(d.memories); setTotal(d.total);
    } else {
      const d = await searchMemories(q); setMemories(d.results); setTotal(d.results.length);
    }
  };

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
          <Brain size={20} strokeWidth={1.8} color="#78909C" />
          <div>
            <p style={{ fontSize: 16, fontWeight: 600, color: "#ECEFF1" }}>Memoria</p>
            <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#455A64", marginTop: 4 }}>
              {total} recuerdos almacenados
            </p>
          </div>
        </div>

        {/* Search */}
        <div style={{ padding: "24px 40px", borderBottom: "1px solid rgba(255,255,255,0.04)", flexShrink: 0 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 12,
            padding: "13px 20px", borderRadius: 12, maxWidth: 520,
            background: "#1E2427", border: "1px solid rgba(255,255,255,0.06)",
          }}>
            <Search size={15} strokeWidth={1.8} color="#455A64" />
            <input value={query} onChange={handleSearch}
              placeholder="Buscar en la memoria..."
              style={{
                flex: 1, background: "transparent", border: "none", outline: "none",
                fontSize: 14, color: "#ECEFF1", fontFamily: "inherit",
              }} />
          </div>
        </div>

        {/* Grid */}
        <div style={{ flex: 1, overflowY: "auto", padding: "28px 40px" }}>
          {loading ? (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 160 }}>
              <span style={{ fontSize: 14, color: "#455A64" }}>Cargando recuerdos...</span>
            </div>
          ) : memories.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 160, gap: 12 }}>
              <Brain size={32} strokeWidth={1.3} color="#263238" />
              <span style={{ fontSize: 14, color: "#455A64" }}>
                {query ? "Sin resultados para esa búsqueda" : "Aún no hay recuerdos"}
              </span>
            </div>
          ) : (
            <div style={{ display: "grid", gap: 14, maxWidth: 680 }}>
              {memories.map(mem => <MemoryCard key={mem.id} mem={mem} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
