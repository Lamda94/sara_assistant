"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import Sidebar from "@/components/Sidebar";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.luismendezdev.online";
const SESSION_ID = "lamda94-web";

const NODE_COLORS: Record<string, string> = {
  tecnología: "#455A64",
  proyecto:   "#37474F",
  persona:    "#4A5568",
  concepto:   "#2E3B45",
  lugar:      "#3A4A52",
  default:    "#2C3A42",
};

const NODE_BORDER: Record<string, string> = {
  tecnología: "#78909C",
  proyecto:   "#607D8B",
  persona:    "#90A4AE",
  concepto:   "#546E7A",
  lugar:      "#819CA9",
  default:    "#546E7A",
};

interface Node { id: string; label: string; type: string; x?: number; y?: number; vx?: number; vy?: number; }
interface Edge { source: string; target: string; relation: string; }
interface Graph { nodes: Node[]; edges: Edge[]; }

// Simple force-directed layout (sin librería externa)
function useForceLayout(nodes: Node[], edges: Edge[]) {
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  const frameRef = useRef<number>(0);

  useEffect(() => {
    if (!nodes.length) return;

    const W = 900, H = 560, CX = W / 2, CY = H / 2;
    const angle = (2 * Math.PI) / nodes.length;

    // Posición inicial en círculo
    const pos: Record<string, { x: number; y: number; vx: number; vy: number }> = {};
    nodes.forEach((n, i) => {
      const r = Math.min(W, H) * 0.32;
      pos[n.id] = {
        x: CX + r * Math.cos(angle * i),
        y: CY + r * Math.sin(angle * i),
        vx: 0, vy: 0,
      };
    });

    let tick = 0;
    const simulate = () => {
      if (tick++ > 200) return; // convergencia
      const REPEL = 3500, ATTRACT = 0.03, DAMP = 0.85, CENTER = 0.005;

      // Repulsión entre todos los nodos
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = pos[nodes[i].id], b = pos[nodes[j].id];
          const dx = a.x - b.x, dy = a.y - b.y;
          const d = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
          const f = REPEL / (d * d);
          a.vx += (dx / d) * f; a.vy += (dy / d) * f;
          b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
        }
      }

      // Atracción por aristas
      edges.forEach(e => {
        const a = pos[e.source], b = pos[e.target];
        if (!a || !b) return;
        const dx = b.x - a.x, dy = b.y - a.y;
        a.vx += dx * ATTRACT; a.vy += dy * ATTRACT;
        b.vx -= dx * ATTRACT; b.vy -= dy * ATTRACT;
      });

      // Gravedad al centro + damping + límites
      nodes.forEach(n => {
        const p = pos[n.id];
        p.vx += (CX - p.x) * CENTER;
        p.vy += (CY - p.y) * CENTER;
        p.vx *= DAMP; p.vy *= DAMP;
        p.x = Math.max(80, Math.min(W - 80, p.x + p.vx));
        p.y = Math.max(40, Math.min(H - 40, p.y + p.vy));
      });

      setPositions(Object.fromEntries(nodes.map(n => [n.id, { x: pos[n.id].x, y: pos[n.id].y }])));
      frameRef.current = requestAnimationFrame(simulate);
    };

    frameRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(frameRef.current);
  }, [nodes, edges]);

  return positions;
}

export default function KnowledgePage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Node | null>(null);

  useEffect(() => {
    fetch(`${BASE_URL}/knowledge/${SESSION_ID}`)
      .then(r => r.json())
      .then(d => { setGraph(d); setLoading(false); })
      .catch(() => { setError("Error cargando el grafo"); setLoading(false); });
  }, []);

  const positions = useForceLayout(graph.nodes, graph.edges);

  const connectedEdges = selected
    ? graph.edges.filter(e => e.source === selected.id || e.target === selected.id)
    : [];

  const getLabel = useCallback((id: string) =>
    graph.nodes.find(n => n.id === id)?.label ?? id,
  [graph.nodes]);

  const W = 900, H = 560;

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#13151A", color: "#ECEFF1" }}>
      <Sidebar active="knowledge" />
      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>

        {/* Header */}
        <div style={{
          padding: "24px 32px 20px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          background: "#0D0F12",
        }}>
          <div style={{ fontSize: 11, color: "#455A64", letterSpacing: 2, marginBottom: 6 }}>
            KNOWLEDGE GRAPH
          </div>
          <div style={{ fontSize: 18, fontWeight: 600, color: "#ECEFF1" }}>
            Grafo de Conocimiento
          </div>
          <div style={{ fontSize: 12, color: "#546E7A", marginTop: 4 }}>
            {graph.nodes.length} nodos · {graph.edges.length} relaciones
          </div>
        </div>

        {loading ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ color: "#455A64", fontSize: 13 }}>Cargando grafo...</div>
          </div>
        ) : error ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ color: "#546E7A", fontSize: 13 }}>{error}</div>
          </div>
        ) : graph.nodes.length === 0 ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
            <div style={{ fontSize: 32, color: "#1E2427" }}>◉</div>
            <div style={{ color: "#455A64", fontSize: 13 }}>Sin conocimiento aún</div>
            <div style={{ color: "#37474F", fontSize: 11 }}>
              Conversa con SARA para que empiece a construir el grafo
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex" }}>

            {/* Grafo SVG */}
            <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
              <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} style={{ display: "block" }}>
                <defs>
                  <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
                    <path d="M0,0 L0,6 L6,3 z" fill="rgba(69,90,100,0.6)" />
                  </marker>
                </defs>

                {/* Aristas */}
                {graph.edges.map((e, i) => {
                  const sp = positions[e.source], tp = positions[e.target];
                  if (!sp || !tp) return null;
                  const isHighlighted = selected && (e.source === selected.id || e.target === selected.id);
                  const mx = (sp.x + tp.x) / 2, my = (sp.y + tp.y) / 2;
                  return (
                    <g key={i}>
                      <line
                        x1={sp.x} y1={sp.y} x2={tp.x} y2={tp.y}
                        stroke={isHighlighted ? "rgba(120,144,156,0.7)" : "rgba(55,71,79,0.4)"}
                        strokeWidth={isHighlighted ? 1.5 : 1}
                        markerEnd="url(#arrow)"
                      />
                      <text x={mx} y={my - 6} textAnchor="middle"
                        style={{ fontSize: 9, fill: isHighlighted ? "#78909C" : "#37474F", userSelect: "none" }}>
                        {e.relation}
                      </text>
                    </g>
                  );
                })}

                {/* Nodos */}
                {graph.nodes.map(n => {
                  const p = positions[n.id];
                  if (!p) return null;
                  const isSelected = selected?.id === n.id;
                  const bg = NODE_COLORS[n.type] ?? NODE_COLORS.default;
                  const border = NODE_BORDER[n.type] ?? NODE_BORDER.default;
                  return (
                    <g key={n.id} onClick={() => setSelected(isSelected ? null : n)}
                      style={{ cursor: "pointer" }}>
                      <circle cx={p.x} cy={p.y} r={isSelected ? 28 : 22}
                        fill={bg}
                        stroke={isSelected ? "#90A4AE" : border}
                        strokeWidth={isSelected ? 2 : 1}
                      />
                      <text x={p.x} y={p.y + 4} textAnchor="middle"
                        style={{ fontSize: 10, fill: isSelected ? "#ECEFF1" : "#B0BEC5",
                          fontWeight: isSelected ? 600 : 400, userSelect: "none" }}>
                        {n.label.length > 12 ? n.label.slice(0, 11) + "…" : n.label}
                      </text>
                      <text x={p.x} y={p.y + (isSelected ? 46 : 38)} textAnchor="middle"
                        style={{ fontSize: 8, fill: "#455A64", letterSpacing: 0.8, userSelect: "none" }}>
                        {n.type.toUpperCase()}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Panel lateral — detalle del nodo seleccionado */}
            {selected && (
              <div style={{
                width: 260,
                borderLeft: "1px solid rgba(255,255,255,0.05)",
                background: "#0D0F12",
                padding: 24,
                display: "flex",
                flexDirection: "column",
                gap: 16,
              }}>
                <div>
                  <div style={{ fontSize: 9, color: "#455A64", letterSpacing: 1.5, marginBottom: 8 }}>
                    NODO SELECCIONADO
                  </div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: "#ECEFF1" }}>{selected.label}</div>
                  <div style={{
                    display: "inline-block", marginTop: 6, padding: "2px 8px",
                    background: NODE_COLORS[selected.type] ?? NODE_COLORS.default,
                    border: `1px solid ${NODE_BORDER[selected.type] ?? NODE_BORDER.default}`,
                    borderRadius: 4, fontSize: 9, color: "#90A4AE", letterSpacing: 1,
                  }}>
                    {selected.type.toUpperCase()}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 9, color: "#455A64", letterSpacing: 1.5, marginBottom: 10 }}>
                    RELACIONES ({connectedEdges.length})
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {connectedEdges.length === 0 && (
                      <div style={{ fontSize: 11, color: "#37474F" }}>Sin conexiones</div>
                    )}
                    {connectedEdges.map((e, i) => {
                      const isSource = e.source === selected.id;
                      const other = getLabel(isSource ? e.target : e.source);
                      return (
                        <div key={i} style={{
                          padding: "8px 10px",
                          background: "#141618",
                          border: "1px solid rgba(255,255,255,0.04)",
                          borderRadius: 6,
                          fontSize: 11,
                        }}>
                          <span style={{ color: "#78909C" }}>
                            {isSource ? "→" : "←"}
                          </span>
                          <span style={{ color: "#546E7A", margin: "0 5px" }}>{e.relation}</span>
                          <span style={{ color: "#90A4AE" }}>{other}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
