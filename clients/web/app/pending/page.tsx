"use client";
import { signOut, useSession } from "next-auth/react";
import { Clock } from "lucide-react";

export default function PendingPage() {
  const { data: session } = useSession();
  const user = session?.user as any;

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.icon}>
          <Clock size={28} color="#78909C" strokeWidth={1.5} />
        </div>
        <h1 style={styles.title}>Acceso pendiente</h1>
        <p style={styles.body}>
          Tu solicitud ha sido registrada. El creador revisará tu acceso
          y recibirás confirmación cuando sea aprobado.
        </p>
        {user?.email && (
          <div style={styles.emailBadge}>{user.email}</div>
        )}
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          style={styles.button}
          onMouseEnter={e => (e.currentTarget.style.borderColor = "#546E7A")}
          onMouseLeave={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#1A1C1E",
  },
  card: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 20,
    padding: "52px 48px",
    borderRadius: 20,
    background: "#1E2225",
    border: "1px solid rgba(255,255,255,0.06)",
    width: 380,
    textAlign: "center",
  },
  icon: {
    width: 60,
    height: 60,
    borderRadius: "50%",
    background: "#1A1C1E",
    border: "1px solid rgba(255,255,255,0.06)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    color: "#ECEFF1",
    margin: 0,
  },
  body: {
    fontSize: 13,
    color: "#546E7A",
    margin: 0,
    lineHeight: 1.7,
  },
  emailBadge: {
    fontSize: 12,
    color: "#78909C",
    background: "#263238",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: 8,
    padding: "6px 14px",
  },
  button: {
    marginTop: 8,
    padding: "11px 28px",
    borderRadius: 10,
    background: "transparent",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#546E7A",
    fontSize: 13,
    cursor: "pointer",
    transition: "border-color 0.15s",
  },
};
