"use client";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      const user = session?.user as any;
      if (user?.approved) {
        router.replace("/");
      } else {
        router.replace("/pending");
      }
    }
  }, [status, session, router]);

  if (status === "loading") {
    return (
      <div style={styles.container}>
        <div style={styles.dot} />
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.avatar}>S</div>
        <h1 style={styles.title}>SARA</h1>
        <p style={styles.subtitle}>Sistema de Asistencia con<br />Reconocimiento Adaptativo</p>

        <button
          onClick={() => signIn("google", { callbackUrl: "/" })}
          style={styles.button}
          onMouseEnter={e => (e.currentTarget.style.background = "#37474F")}
          onMouseLeave={e => (e.currentTarget.style.background = "#263238")}
        >
          <GoogleIcon />
          <span>Continuar con Google</span>
        </button>

        <p style={styles.note}>El acceso requiere autorización del creador</p>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" style={{ flexShrink: 0 }}>
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
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
    width: 360,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    background: "#263238",
    border: "1px solid #455A64",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 22,
    fontWeight: 700,
    color: "#78909C",
  },
  title: {
    fontSize: 28,
    fontWeight: 700,
    color: "#ECEFF1",
    margin: 0,
    letterSpacing: "0.06em",
  },
  subtitle: {
    fontSize: 13,
    color: "#546E7A",
    margin: 0,
    textAlign: "center",
    lineHeight: 1.6,
  },
  button: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "13px 24px",
    borderRadius: 12,
    background: "#263238",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#ECEFF1",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    width: "100%",
    justifyContent: "center",
    transition: "background 0.15s",
    marginTop: 8,
  },
  note: {
    fontSize: 11,
    color: "#37474F",
    margin: 0,
    textAlign: "center",
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#455A64",
  },
};
