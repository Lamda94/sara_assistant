"use client";
import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Save, Plus, Trash2, Power, ArrowLeft, Briefcase, Upload, Loader } from "lucide-react";
import Sidebar from "@/components/Sidebar";

const BASE = "/api";
const SESSION_ID = "lamda94-web";

interface Portal {
  id?: number;
  company_name: string;
  careers_url: string;
  ats_provider: string | null;
  enabled?: boolean;
}

export default function CareerSetupPage() {
  const { status } = useSession();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [careerMode, setCareerMode] = useState(false);
  const [tab, setTab] = useState<"profile" | "portals">("profile");

  // Profile fields
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [portfolio, setPortfolio] = useState("");
  const [github, setGithub] = useState("");
  const [cvMarkdown, setCvMarkdown] = useState("");
  const [targetRoles, setTargetRoles] = useState("");
  const [compMin, setCompMin] = useState("");
  const [compMax, setCompMax] = useState("");
  const [compCurrency, setCompCurrency] = useState("USD");
  const [titlePositive, setTitlePositive] = useState("");
  const [titleNegative, setTitleNegative] = useState("");
  const [scanInterval, setScanInterval] = useState(6);
  const [minScore, setMinScore] = useState(4.0);

  // Portals
  const [portals, setPortals] = useState<Portal[]>([]);
  const [newCompany, setNewCompany] = useState("");
  const [newUrl, setNewUrl] = useState("");

  useEffect(() => {
    if (status !== "authenticated") return;
    loadAll();
  }, [status]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [pRes, ptRes, sRes] = await Promise.all([
        fetch(`${BASE}/career/profile?session_id=${SESSION_ID}`),
        fetch(`${BASE}/career/portals?session_id=${SESSION_ID}`),
        fetch(`${BASE}/career/status?session_id=${SESSION_ID}`),
      ]);

      if (pRes.ok) {
        const data = await pRes.json();
        const p = data.profile;
        if (p) {
          setFullName(p.full_name || "");
          setEmail(p.email || "");
          setPhone(p.phone || "");
          setLocation(p.location || "");
          setLinkedin(p.linkedin_url || "");
          setPortfolio(p.portfolio_url || "");
          setGithub(p.github_url || "");
          setCvMarkdown(p.cv_markdown || "");
          setTargetRoles((p.target_roles || []).join(", "));
          setCompMin(p.compensation?.min?.toString() || "");
          setCompMax(p.compensation?.max?.toString() || "");
          setCompCurrency(p.compensation?.currency || "USD");
          setTitlePositive((p.title_positive || []).join(", "));
          setTitleNegative((p.title_negative || []).join(", "));
          setScanInterval(p.scan_interval_hours || 6);
          setMinScore(p.min_score_cv || 4.0);
        }
      }
      if (ptRes.ok) setPortals(await ptRes.json());
      if (sRes.ok) {
        const s = await sRes.json();
        setCareerMode(s.career_mode);
      }
    } finally {
      setLoading(false);
    }
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      const body = {
        full_name: fullName,
        email: email || null,
        phone: phone || null,
        location: location || null,
        linkedin_url: linkedin || null,
        portfolio_url: portfolio || null,
        github_url: github || null,
        cv_markdown: cvMarkdown || null,
        target_roles: targetRoles ? targetRoles.split(",").map(r => r.trim()).filter(Boolean) : null,
        compensation: compMin || compMax ? { min: Number(compMin) || 0, max: Number(compMax) || 0, currency: compCurrency } : null,
        title_positive: titlePositive ? titlePositive.split(",").map(k => k.trim()).filter(Boolean) : null,
        title_negative: titleNegative ? titleNegative.split(",").map(k => k.trim()).filter(Boolean) : null,
        scan_interval_hours: scanInterval,
        min_score_cv: minScore,
      };

      await fetch(`${BASE}/career/profile?session_id=${SESSION_ID}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
    } finally {
      setSaving(false);
    }
  };

  const toggleMode = async () => {
    const res = await fetch(`${BASE}/career/toggle?session_id=${SESSION_ID}`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      if (data.error) {
        alert(data.error);
      } else {
        setCareerMode(data.career_mode);
      }
    }
  };

  const uploadCV = async (file: File) => {
    setParsing(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${BASE}/career/parse-cv`, { method: "POST", body: formData });
      if (!res.ok) throw new Error("Error procesando CV");
      const data = await res.json();
      if (data.error) {
        alert(data.error);
        return;
      }
      const p = data.profile;
      if (p.full_name) setFullName(p.full_name);
      if (p.email) setEmail(p.email);
      if (p.phone) setPhone(p.phone);
      if (p.location) setLocation(p.location);
      if (p.linkedin_url) setLinkedin(p.linkedin_url);
      if (p.portfolio_url) setPortfolio(p.portfolio_url);
      if (p.github_url) setGithub(p.github_url);
      if (p.cv_markdown) setCvMarkdown(p.cv_markdown);
      if (p.target_roles) setTargetRoles(p.target_roles.join(", "));
      if (p.title_positive) setTitlePositive(p.title_positive.join(", "));
      if (p.title_negative) setTitleNegative(p.title_negative.join(", "));
    } catch (e) {
      alert("Error al procesar el CV");
    } finally {
      setParsing(false);
    }
  };

  const addPortal = async () => {
    if (!newCompany || !newUrl) return;
    const res = await fetch(`${BASE}/career/portals?session_id=${SESSION_ID}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name: newCompany, careers_url: newUrl }),
    });
    if (res.ok) {
      setNewCompany("");
      setNewUrl("");
      const ptRes = await fetch(`${BASE}/career/portals?session_id=${SESSION_ID}`);
      if (ptRes.ok) setPortals(await ptRes.json());
    }
  };

  const removePortal = async (id: number) => {
    await fetch(`${BASE}/career/portals/${id}`, { method: "DELETE" });
    setPortals(portals.filter(p => p.id !== id));
  };

  if (status === "loading" || loading) {
    return (
      <div style={{ display: "flex", height: "100vh", background: "#1A1C1E" }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ color: "#455A64", fontSize: 13 }}>Cargando...</div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#1A1C1E" }}>
      <Sidebar />
      <div style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <button onClick={() => router.push("/career")}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#546E7A", display: "flex", alignItems: "center", padding: 0 }}>
                <ArrowLeft size={18} />
              </button>
              <h1 style={{ fontSize: 22, fontWeight: 700, color: "#ECEFF1", margin: 0 }}>Configurar CareerOps</h1>
            </div>
            <p style={{ fontSize: 13, color: "#546E7A", margin: 0 }}>
              Configura tu perfil, CV y portales para activar la busqueda automatica
            </p>
          </div>
          <button onClick={toggleMode} style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: 10, cursor: "pointer",
            background: careerMode ? "rgba(76,175,80,0.15)" : "rgba(120,144,156,0.15)",
            border: `1px solid ${careerMode ? "#4CAF5040" : "#78909C30"}`,
            color: careerMode ? "#4CAF50" : "#78909C", fontSize: 13, fontWeight: 600,
          }}>
            <Power size={16} />
            {careerMode ? "Desactivar busqueda" : "Activar busqueda"}
          </button>
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          {(["profile", "portals"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              padding: "8px 18px", borderRadius: 9, cursor: "pointer",
              border: "1px solid", fontSize: 13,
              borderColor: tab === t ? "#455A64" : "rgba(255,255,255,0.06)",
              background: tab === t ? "#263238" : "transparent",
              color: tab === t ? "#ECEFF1" : "#546E7A",
              display: "flex", alignItems: "center", gap: 8,
            }}>
              {t === "profile" ? <Briefcase size={14} /> : <Plus size={14} />}
              {t === "profile" ? "Perfil y CV" : `Portales (${portals.length})`}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {tab === "profile" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 700 }}>
            {/* Upload CV */}
            <div style={{
              padding: 24, borderRadius: 12, background: "#1E2225",
              border: "2px dashed rgba(66,165,245,0.25)", textAlign: "center",
              position: "relative",
            }}>
              <input
                type="file"
                accept=".pdf,.txt,.md,.doc,.docx"
                onChange={e => { if (e.target.files?.[0]) uploadCV(e.target.files[0]); }}
                disabled={parsing}
                style={{
                  position: "absolute", inset: 0, opacity: 0, cursor: "pointer",
                  width: "100%", height: "100%",
                }}
              />
              {parsing ? (
                <>
                  <Loader size={28} color="#42A5F5" style={{ animation: "spin 1s linear infinite" }} />
                  <p style={{ color: "#42A5F5", fontSize: 14, fontWeight: 600, margin: "12px 0 4px" }}>
                    Analizando tu CV con IA...
                  </p>
                  <p style={{ color: "#546E7A", fontSize: 12, margin: 0 }}>
                    Extrayendo datos, skills, experiencia y generando perfil
                  </p>
                </>
              ) : (
                <>
                  <Upload size={28} color="#42A5F5" />
                  <p style={{ color: "#ECEFF1", fontSize: 14, fontWeight: 600, margin: "12px 0 4px" }}>
                    Sube tu CV para autocompletar el perfil
                  </p>
                  <p style={{ color: "#546E7A", fontSize: 12, margin: 0 }}>
                    PDF, TXT o Markdown — la IA extraera todos los datos automaticamente
                  </p>
                </>
              )}
            </div>

            {/* Datos basicos */}
            <Section title="Datos basicos">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Input label="Nombre completo *" value={fullName} onChange={setFullName} placeholder="Luis Mendez" />
                <Input label="Email" value={email} onChange={setEmail} placeholder="tu@email.com" />
                <Input label="Telefono" value={phone} onChange={setPhone} placeholder="+57..." />
                <Input label="Ubicacion" value={location} onChange={setLocation} placeholder="Bogota, Colombia" />
                <Input label="LinkedIn" value={linkedin} onChange={setLinkedin} placeholder="https://linkedin.com/in/..." />
                <Input label="Portfolio" value={portfolio} onChange={setPortfolio} placeholder="https://..." />
                <Input label="GitHub" value={github} onChange={setGithub} placeholder="https://github.com/..." />
              </div>
            </Section>

            {/* Roles y busqueda */}
            <Section title="Objetivo de busqueda">
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <Input label="Roles objetivo (separados por coma)" value={targetRoles} onChange={setTargetRoles}
                  placeholder="Senior Backend Engineer, AI Engineer, Tech Lead" />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                  <Input label="Salario minimo" value={compMin} onChange={setCompMin} placeholder="80000" />
                  <Input label="Salario maximo" value={compMax} onChange={setCompMax} placeholder="150000" />
                  <Input label="Moneda" value={compCurrency} onChange={setCompCurrency} placeholder="USD" />
                </div>
                <Input label="Keywords positivos (titulo debe contener al menos uno)" value={titlePositive} onChange={setTitlePositive}
                  placeholder="AI, ML, Backend, Python, Engineer, Lead" />
                <Input label="Keywords negativos (excluir si contiene)" value={titleNegative} onChange={setTitleNegative}
                  placeholder="Junior, Intern, .NET, Java, PHP" />
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label style={labelStyle}>Escaneo cada (horas)</label>
                    <input type="number" min={1} max={48} value={scanInterval}
                      onChange={e => setScanInterval(Number(e.target.value))}
                      style={inputStyle} />
                  </div>
                  <div>
                    <label style={labelStyle}>Score minimo para generar CV</label>
                    <input type="number" min={1} max={5} step={0.5} value={minScore}
                      onChange={e => setMinScore(Number(e.target.value))}
                      style={inputStyle} />
                  </div>
                </div>
              </div>
            </Section>

            {/* CV */}
            <Section title="CV (Markdown)">
              <textarea
                value={cvMarkdown}
                onChange={e => setCvMarkdown(e.target.value)}
                placeholder={"# Tu Nombre\n\n## Experiencia\n\n### Empresa — Cargo (2022-2024)\n- Logro 1\n- Logro 2\n\n## Educacion\n\n## Skills"}
                style={{
                  ...inputStyle,
                  minHeight: 300, resize: "vertical", fontFamily: "monospace", fontSize: 12, lineHeight: "1.6",
                }}
              />
              <p style={{ fontSize: 11, color: "#455A64", marginTop: 6 }}>
                Pega tu CV en formato Markdown. Este es el documento base que se personaliza para cada oferta.
              </p>
            </Section>

            {/* Save */}
            <button onClick={saveProfile} disabled={saving || !fullName} style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "12px 24px", borderRadius: 10, cursor: fullName ? "pointer" : "not-allowed",
              background: fullName ? "#263238" : "#1E2225",
              border: "1px solid #455A64", color: "#ECEFF1", fontSize: 14, fontWeight: 600,
              opacity: saving ? 0.6 : 1, width: "100%",
            }}>
              <Save size={16} />
              {saving ? "Guardando..." : "Guardar perfil"}
            </button>
          </div>
        )}

        {/* Portals Tab */}
        {tab === "portals" && (
          <div style={{ maxWidth: 700 }}>
            {/* Add portal */}
            <div style={{
              display: "flex", gap: 10, marginBottom: 20, padding: 16,
              background: "#1E2225", borderRadius: 12, border: "1px solid rgba(255,255,255,0.05)",
            }}>
              <input value={newCompany} onChange={e => setNewCompany(e.target.value)}
                placeholder="Nombre empresa" style={{ ...inputStyle, flex: 1 }} />
              <input value={newUrl} onChange={e => setNewUrl(e.target.value)}
                placeholder="URL de careers (ej: https://jobs.ashbyhq.com/company)"
                style={{ ...inputStyle, flex: 2 }} />
              <button onClick={addPortal} disabled={!newCompany || !newUrl} style={{
                display: "flex", alignItems: "center", gap: 6, padding: "8px 16px",
                borderRadius: 8, cursor: newCompany && newUrl ? "pointer" : "not-allowed",
                background: "#263238", border: "1px solid #455A64", color: "#ECEFF1", fontSize: 12,
              }}>
                <Plus size={14} /> Agregar
              </button>
            </div>

            {/* Portal list */}
            {portals.length === 0 ? (
              <div style={{ color: "#37474F", fontSize: 13, padding: "32px 0" }}>
                No hay portales configurados. Agrega empresas donde quieras buscar ofertas.
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {portals.map(p => (
                  <div key={p.id} style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "14px 20px", borderRadius: 12, background: "#1E2225",
                    border: "1px solid rgba(255,255,255,0.05)",
                  }}>
                    <div>
                      <p style={{ margin: 0, fontSize: 14, color: "#ECEFF1", fontWeight: 500 }}>
                        {p.company_name}
                      </p>
                      <p style={{ margin: "3px 0 0", fontSize: 11, color: "#546E7A" }}>
                        {p.careers_url}
                        {p.ats_provider && (
                          <span style={{
                            marginLeft: 8, fontSize: 10, padding: "2px 6px", borderRadius: 4,
                            background: "rgba(66,165,245,0.12)", color: "#42A5F5",
                          }}>
                            {p.ats_provider}
                          </span>
                        )}
                      </p>
                    </div>
                    <button onClick={() => p.id && removePortal(p.id)} style={{
                      background: "none", border: "none", cursor: "pointer", color: "#EF5350", padding: 6,
                    }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <p style={{ fontSize: 11, color: "#455A64", marginTop: 16 }}>
              Soporta portales de Greenhouse, Ashby, Lever y Workday. El ATS se detecta automaticamente por la URL.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Components ──────────────────────────────────────────────────────

const labelStyle: React.CSSProperties = {
  fontSize: 11, color: "#78909C", textTransform: "uppercase", letterSpacing: "0.05em",
  display: "block", marginBottom: 6,
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "10px 14px", borderRadius: 8, fontSize: 13,
  background: "#141618", border: "1px solid rgba(255,255,255,0.08)",
  color: "#ECEFF1", outline: "none",
};

function Input({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} style={inputStyle} />
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      padding: 20, borderRadius: 12, background: "#1E2225",
      border: "1px solid rgba(255,255,255,0.05)",
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: "#78909C", margin: "0 0 16px",
        textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {title}
      </h3>
      {children}
    </div>
  );
}
