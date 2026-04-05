"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { MessageSquare, Archive, Brain, Settings, Network, Shield, Users, LogOut, ClipboardCheck, TrendingUp } from "lucide-react";

const NAV = [
  { href: "/",           icon: MessageSquare, label: "Conversación" },
  { href: "/memory",     icon: Brain,         label: "Memoria"      },
  { href: "/commitments", icon: ClipboardCheck, label: "Compromisos" },
  { href: "/knowledge",  icon: Network,       label: "Grafo"        },
  { href: "/betting",     icon: TrendingUp,    label: "SABE"         },
  { href: "/archives",   icon: Archive,       label: "Archivos"     },
  { href: "/parental",   icon: Shield,        label: "Dispositivos" },
  { href: "/settings",   icon: Settings,      label: "Ajustes"      },
];

const CREATOR_NAV = [
  { href: "/admin/users", icon: Users, label: "Usuarios" },
];

export default function Sidebar() {
  const path = usePathname();
  const { data: session } = useSession();
  const user = session?.user as any;
  const isCreator = user?.isCreator;

  const allNav = isCreator ? [...NAV, ...CREATOR_NAV] : NAV;
  const initials = user?.name
    ? user.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase()
    : (user?.email?.[0] ?? "?").toUpperCase();

  return (
    <aside style={{
      width: 220,
      background: "#141618",
      borderRight: "1px solid rgba(255,255,255,0.05)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: "28px 24px 24px", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
        <p style={{ fontSize: 17, fontWeight: 700, color: "#ECEFF1", letterSpacing: "-0.01em" }}>SARA</p>
        <p style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", color: "#455A64", marginTop: 5 }}>
          Asistente Adaptativo
        </p>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "20px 14px", display: "flex", flexDirection: "column", gap: 4 }}>
        {allNav.map(({ href, icon: Icon, label }) => {
          const active = path === href;
          return (
            <Link key={href} href={href} style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "13px 14px",
              borderRadius: 10,
              background: active ? "rgba(69,90,100,0.25)" : "transparent",
              color: active ? "#ECEFF1" : "#455A64",
              borderLeft: active ? "2px solid #78909C" : "2px solid transparent",
              textDecoration: "none",
              transition: "all 0.15s",
              fontSize: 12,
              fontWeight: active ? 500 : 400,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}>
              <Icon size={15} strokeWidth={1.8} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div style={{
        padding: "16px 20px",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: "50%",
          background: "#263238", border: "1px solid #455A64",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
          overflow: "hidden",
        }}>
          {user?.image
            ? <img src={user.image} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            : <span style={{ fontSize: 12, fontWeight: 700, color: "#78909C" }}>{initials}</span>
          }
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#ECEFF1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", margin: 0 }}>
            {user?.name ?? user?.email ?? "—"}
          </p>
          <p style={{ fontSize: 11, color: "#455A64", marginTop: 2, margin: "2px 0 0" }}>
            {isCreator ? "Creador" : "Usuario"}
          </p>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          title="Cerrar sesión"
          style={{ background: "none", border: "none", cursor: "pointer", color: "#37474F", padding: 4, flexShrink: 0 }}
          onMouseEnter={e => (e.currentTarget.style.color = "#78909C")}
          onMouseLeave={e => (e.currentTarget.style.color = "#37474F")}
        >
          <LogOut size={14} strokeWidth={1.8} />
        </button>
      </div>
    </aside>
  );
}
