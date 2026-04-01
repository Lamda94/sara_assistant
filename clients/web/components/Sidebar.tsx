"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, Archive, Brain, Settings, Network, Shield } from "lucide-react";

const NAV = [
  { href: "/",           icon: MessageSquare, label: "Conversación" },
  { href: "/memory",     icon: Brain,         label: "Memoria"      },
  { href: "/knowledge",  icon: Network,       label: "Grafo"        },
  { href: "/archives",   icon: Archive,       label: "Archivos"     },
  { href: "/parental",   icon: Shield,        label: "Dispositivos" },
  { href: "/settings",   icon: Settings,      label: "Ajustes"      },
];

export default function Sidebar({ active }: { active?: string }) {
  const path = usePathname();
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
        {NAV.map(({ href, icon: Icon, label }) => {
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
        padding: "20px 20px",
        borderTop: "1px solid rgba(255,255,255,0.05)",
        display: "flex",
        alignItems: "center",
        gap: 12,
      }}>
        <div style={{
          width: 34, height: 34, borderRadius: "50%",
          background: "#263238", border: "1px solid #455A64",
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "#78909C" }}>L</span>
        </div>
        <div style={{ minWidth: 0 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: "#ECEFF1", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            lamda94
          </p>
          <p style={{ fontSize: 11, color: "#455A64", marginTop: 2 }}>Creador</p>
        </div>
      </div>
    </aside>
  );
}
