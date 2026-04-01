"use client";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Check, X, Clock, UserCheck } from "lucide-react";
import Sidebar from "@/components/Sidebar";

const BACKEND = "/api";

type UserEntry = {
  email: string;
  name: string | null;
  requested_at?: string;
  approved_at?: string;
};

export default function AdminUsersPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const user = session?.user as any;

  const [pending, setPending] = useState<UserEntry[]>([]);
  const [approved, setApproved] = useState<UserEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pending" | "approved">("pending");

  useEffect(() => {
    if (status === "authenticated" && !user?.isCreator) {
      router.replace("/");
    }
  }, [status, user, router]);

  const load = async () => {
    setLoading(true);
    try {
      const [pRes, aRes] = await Promise.all([
        fetch(`${BACKEND}/auth/pending`),
        fetch(`${BACKEND}/auth/approved`),
      ]);
      setPending(await pRes.json());
      setApproved(await aRes.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const approve = async (email: string) => {
    await fetch(`${BACKEND}/auth/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    await load();
  };

  const revoke = async (email: string) => {
    await fetch(`${BACKEND}/auth/revoke?email=${encodeURIComponent(email)}`, { method: "DELETE" });
    await load();
  };

  if (status === "loading" || loading) {
    return (
      <div style={{ display: "flex", height: "100vh", background: "#1A1C1E" }}>
        <Sidebar />
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#455A64" }} />
        </div>
      </div>
    );
  }

  const list = tab === "pending" ? pending : approved;

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "#1A1C1E" }}>
      <Sidebar />
      <div style={{ flex: 1, overflowY: "auto", padding: "40px 48px" }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "#ECEFF1", margin: "0 0 6px" }}>
          Gestión de usuarios
        </h1>
        <p style={{ fontSize: 13, color: "#546E7A", margin: "0 0 32px" }}>
          Aprueba o revoca acceso a la plataforma web
        </p>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          {(["pending", "approved"] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                padding: "8px 18px",
                borderRadius: 9,
                border: "1px solid",
                borderColor: tab === t ? "#455A64" : "rgba(255,255,255,0.06)",
                background: tab === t ? "#263238" : "transparent",
                color: tab === t ? "#ECEFF1" : "#546E7A",
                fontSize: 13,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              {t === "pending" ? <Clock size={14} /> : <UserCheck size={14} />}
              {t === "pending" ? `Pendientes (${pending.length})` : `Aprobados (${approved.length})`}
            </button>
          ))}
        </div>

        {/* List */}
        {list.length === 0 ? (
          <div style={{ color: "#37474F", fontSize: 13, padding: "32px 0" }}>
            {tab === "pending" ? "No hay solicitudes pendientes." : "No hay usuarios aprobados."}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {list.map(u => (
              <div key={u.email} style={{
                display: "flex", alignItems: "center", justifyContent: "space-between",
                padding: "16px 20px",
                borderRadius: 12,
                background: "#1E2225",
                border: "1px solid rgba(255,255,255,0.05)",
              }}>
                <div>
                  <p style={{ margin: 0, fontSize: 14, color: "#ECEFF1", fontWeight: 500 }}>
                    {u.name ?? u.email}
                  </p>
                  {u.name && (
                    <p style={{ margin: "3px 0 0", fontSize: 12, color: "#546E7A" }}>{u.email}</p>
                  )}
                  <p style={{ margin: "4px 0 0", fontSize: 11, color: "#37474F" }}>
                    {tab === "pending"
                      ? `Solicitó: ${u.requested_at ? new Date(u.requested_at).toLocaleString("es") : "—"}`
                      : `Aprobado: ${u.approved_at ? new Date(u.approved_at).toLocaleString("es") : "—"}`}
                  </p>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {tab === "pending" && (
                    <ActionBtn icon={<Check size={14} />} label="Aprobar" color="#4CAF50" onClick={() => approve(u.email)} />
                  )}
                  {tab === "approved" && (
                    <ActionBtn icon={<X size={14} />} label="Revocar" color="#EF5350" onClick={() => revoke(u.email)} />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ActionBtn({ icon, label, color, onClick }: {
  icon: React.ReactNode; label: string; color: string; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "7px 14px",
        borderRadius: 8,
        background: "transparent",
        border: `1px solid ${color}33`,
        color,
        fontSize: 12,
        cursor: "pointer",
        transition: "background 0.15s",
      }}
      onMouseEnter={e => (e.currentTarget.style.background = `${color}18`)}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
    >
      {icon}
      {label}
    </button>
  );
}
