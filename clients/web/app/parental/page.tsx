"use client";
import { useEffect, useState } from "react";
import { Shield, Smartphone, ToggleLeft, ToggleRight, Edit2, Check, RefreshCw } from "lucide-react";
import Sidebar from "@/components/Sidebar";

const API = "/api";
const PARENT_ID = "lamda94";

interface Device {
  child_session_id: string;
  label: string;
  monitoring_enabled: boolean;
  last_seen: string | null;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "Nunca";
  const diff = Date.now() - new Date(iso + "Z").getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "Ahora mismo";
  if (m < 60) return `Hace ${m} min`;
  const h = Math.floor(m / 60);
  if (h < 24) return `Hace ${h}h`;
  return `Hace ${Math.floor(h / 24)}d`;
}

export default function ParentalPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/monitoring/children/${PARENT_ID}`);
      const data = await res.json();
      setDevices(data.map((d: any) => ({
        child_session_id: d.child_session_id,
        label: d.label,
        monitoring_enabled: d.monitoring_enabled ?? false,
        last_seen: d.last_seen,
      })));
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchDevices(); }, []);

  const toggleMonitoring = async (id: string, current: boolean) => {
    await fetch(`${API}/monitoring/device/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monitoring_enabled: !current }),
    });
    setDevices(prev => prev.map(d =>
      d.child_session_id === id ? { ...d, monitoring_enabled: !current } : d
    ));
  };

  const saveLabel = async (id: string) => {
    await fetch(`${API}/monitoring/device/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ device_label: editLabel }),
    });
    setDevices(prev => prev.map(d =>
      d.child_session_id === id ? { ...d, label: editLabel } : d
    ));
    setEditingId(null);
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: "#1A1C1E", fontFamily: "system-ui, sans-serif" }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <Shield size={22} color="#455A64" />
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 600, color: "#ECEFF1", margin: 0 }}>Dispositivos supervisados</h1>
              <p style={{ fontSize: 12, color: "#455A64", margin: "4px 0 0" }}>
                Activa el monitoreo remotamente en cada dispositivo
              </p>
            </div>
          </div>
          <button
            onClick={fetchDevices}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#455A64", display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
          >
            <RefreshCw size={14} />
            Actualizar
          </button>
        </div>

        {loading ? (
          <p style={{ color: "#455A64", fontSize: 13 }}>Cargando dispositivos…</p>
        ) : devices.length === 0 ? (
          <div style={{
            padding: 40, textAlign: "center", border: "1px dashed rgba(255,255,255,0.08)",
            borderRadius: 14, color: "#455A64"
          }}>
            <Smartphone size={32} style={{ marginBottom: 12, opacity: 0.4 }} />
            <p style={{ fontSize: 14, margin: 0 }}>Ningún dispositivo registrado todavía.</p>
            <p style={{ fontSize: 12, margin: "8px 0 0", opacity: 0.6 }}>
              Instala la app SARA en el dispositivo del hijo. Se registrará automáticamente.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {devices.map(device => (
              <div key={device.child_session_id} style={{
                background: "#1E2427",
                borderRadius: 14,
                padding: "20px 24px",
                border: `1px solid ${device.monitoring_enabled ? "rgba(120,144,156,0.25)" : "rgba(255,255,255,0.05)"}`,
                display: "flex",
                alignItems: "center",
                gap: 20,
              }}>
                {/* Icono */}
                <div style={{
                  width: 44, height: 44, borderRadius: 12,
                  background: device.monitoring_enabled ? "rgba(69,90,100,0.3)" : "#212426",
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  <Smartphone size={20} color={device.monitoring_enabled ? "#78909C" : "#37474F"} />
                </div>

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  {editingId === device.child_session_id ? (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <input
                        value={editLabel}
                        onChange={e => setEditLabel(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && saveLabel(device.child_session_id)}
                        autoFocus
                        style={{
                          background: "#263238", border: "1px solid #455A64", borderRadius: 6,
                          color: "#ECEFF1", padding: "4px 10px", fontSize: 14, outline: "none",
                        }}
                      />
                      <button onClick={() => saveLabel(device.child_session_id)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#78909C" }}>
                        <Check size={16} />
                      </button>
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 15, fontWeight: 500, color: "#ECEFF1" }}>{device.label}</span>
                      <button onClick={() => { setEditingId(device.child_session_id); setEditLabel(device.label); }}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#37474F", padding: 0 }}>
                        <Edit2 size={13} />
                      </button>
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 16, marginTop: 4 }}>
                    <span style={{ fontSize: 11, color: "#455A64", fontFamily: "monospace" }}>
                      {device.child_session_id}
                    </span>
                    <span style={{ fontSize: 11, color: "#37474F" }}>
                      {timeAgo(device.last_seen)}
                    </span>
                  </div>
                </div>

                {/* Estado + toggle */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, flexShrink: 0 }}>
                  <span style={{
                    fontSize: 11, padding: "3px 10px", borderRadius: 20,
                    background: device.monitoring_enabled ? "rgba(69,90,100,0.3)" : "rgba(255,255,255,0.04)",
                    color: device.monitoring_enabled ? "#78909C" : "#37474F",
                    border: `1px solid ${device.monitoring_enabled ? "rgba(120,144,156,0.2)" : "rgba(255,255,255,0.06)"}`,
                  }}>
                    {device.monitoring_enabled ? "Activo" : "Inactivo"}
                  </span>
                  <button
                    onClick={() => toggleMonitoring(device.child_session_id, device.monitoring_enabled)}
                    style={{ background: "none", border: "none", cursor: "pointer", display: "flex", alignItems: "center", padding: 0 }}
                    title={device.monitoring_enabled ? "Desactivar monitoreo" : "Activar monitoreo"}
                  >
                    {device.monitoring_enabled
                      ? <ToggleRight size={32} color="#78909C" />
                      : <ToggleLeft size={32} color="#37474F" />
                    }
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Info */}
        <div style={{ marginTop: 32, padding: 16, background: "#1E2427", borderRadius: 10, border: "1px solid rgba(255,255,255,0.04)" }}>
          <p style={{ fontSize: 12, color: "#455A64", margin: 0, lineHeight: 1.6 }}>
            <strong style={{ color: "#78909C" }}>Cómo funciona:</strong> La app SARA instalada en el dispositivo del hijo
            se registra automáticamente al abrirse. Activa el monitoreo aquí y el dispositivo lo
            detectará en los próximos 5 minutos. Pregunta a SARA: <em style={{ color: "#78909C" }}>"¿Qué hizo mi hija hoy en el móvil?"</em>
          </p>
        </div>
      </main>
    </div>
  );
}
