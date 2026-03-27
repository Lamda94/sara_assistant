"use client";
import { Settings, Server, Cpu, Database, Shield } from "lucide-react";
import Sidebar from "@/components/Sidebar";

function Row({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between"
      style={{ padding: "22px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ maxWidth: "55%" }}>
        <p style={{ fontSize: 15, fontWeight: 500, color: "#ECEFF1", marginBottom: sub ? 6 : 0 }}>
          {label}
        </p>
        {sub && (
          <p style={{ fontSize: 12.5, color: "#455A64", lineHeight: 1.5 }}>{sub}</p>
        )}
      </div>
      <span style={{
        fontSize: 13,
        fontFamily: "monospace",
        padding: "6px 16px",
        borderRadius: 8,
        background: "#212426",
        color: "#78909C",
        border: "1px solid rgba(255,255,255,0.06)",
        flexShrink: 0,
        marginLeft: 24,
      }}>
        {value}
      </span>
    </div>
  );
}

function Section({ icon: Icon, title, children }: {
  icon: React.ElementType; title: string; children: React.ReactNode;
}) {
  return (
    <div style={{
      borderRadius: 14,
      overflow: "hidden",
      marginBottom: 28,
      background: "#1E2427",
      border: "1px solid rgba(255,255,255,0.05)",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "18px 28px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        background: "rgba(255,255,255,0.02)",
      }}>
        <Icon size={15} strokeWidth={1.8} color="#78909C" />
        <span style={{
          fontSize: 11,
          textTransform: "uppercase",
          letterSpacing: "0.12em",
          fontWeight: 600,
          color: "#78909C",
        }}>
          {title}
        </span>
      </div>
      <div style={{ padding: "0 28px" }}>
        {children}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0, background: "#1A1C1E" }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "24px 40px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          flexShrink: 0,
        }}>
          <Settings size={20} strokeWidth={1.8} color="#78909C" />
          <div>
            <p style={{ fontSize: 18, fontWeight: 600, color: "#ECEFF1" }}>Configuración</p>
            <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.12em", color: "#455A64", marginTop: 4 }}>
              Sistema SARA v0.1.0
            </p>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: "36px 40px" }}>
          <div style={{ maxWidth: 680 }}>

            <Section icon={Cpu} title="Modelo de Lenguaje">
              <Row label="Proveedor" value="Groq API" />
              <Row label="Modelo" value="llama-3.1-8b-instant" sub="Velocidad optimizada para CPU" />
              <Row label="Temperatura" value="0.7" sub="Balance entre creatividad y precisión" />
              <Row label="Tokens máx." value="1024" />
            </Section>

            <Section icon={Database} title="Memoria Vectorial">
              <Row label="Motor" value="Qdrant" sub="Puerto 6333" />
              <Row label="Colección" value="sara_memories" />
              <Row label="Modelo de embeddings" value="nomic-embed-text" sub="768 dimensiones · Ollama local" />
              <Row label="Recuerdos top-k" value="5" sub="Recuerdos más relevantes por consulta" />
            </Section>

            <Section icon={Server} title="Base de Datos">
              <Row label="Motor" value="PostgreSQL 15" sub="Contenedor tharot-pg" />
              <Row label="Base de datos" value="sara_db" />
              <Row label="Backend" value="FastAPI" sub="Puerto 8000" />
            </Section>

            <Section icon={Shield} title="Identidad">
              <Row label="Nombre" value="SARA" sub="Sistema de Asistencia con Reconocimiento Adaptativo" />
              <Row label="Creador" value="lamda94" sub="Trato especial: formal y respetuoso" />
              <Row label="Idioma" value="Automático" sub="Detectado por el idioma del usuario" />
            </Section>

          </div>
        </div>
      </div>
    </div>
  );
}
