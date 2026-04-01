"use client";
import { useState, useEffect, useRef } from "react";
import { useSession } from "next-auth/react";
import { Search, MoreVertical, Send, Mic, Smile } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { sendChat, getTime, getDateLabel, type Message } from "@/lib/api";

const SESSION_ID = "lamda94-web";

function ThinkingDots() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>
      {[0, 150, 300].map((d) => (
        <div key={d} style={{
          width: 6, height: 6, borderRadius: "50%", background: "#78909C",
          animation: `bounce 1.3s ease-in-out ${d}ms infinite`,
        }} />
      ))}
    </div>
  );
}

function Bubble({ msg }: { msg: Message & { typing?: boolean } }) {
  const isUser = msg.role === "user";
  return (
    <div className="msg-enter" style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
      <div style={{
        maxWidth: "60%",
        padding: msg.typing ? "16px 20px" : "18px 22px",
        borderRadius: isUser ? "14px 14px 3px 14px" : "14px 14px 14px 3px",
        background: isUser ? "#263238" : "#1E2225",
        border: `1px solid ${isUser ? "rgba(69,90,100,0.3)" : "rgba(255,255,255,0.04)"}`,
        color: isUser ? "#ECEFF1" : "#B0BEC5",
        fontSize: 14,
        lineHeight: 1.7,
      }}>
        {msg.typing ? <ThinkingDots /> : msg.content}
      </div>
      {!msg.typing && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, padding: "0 4px" }}>
          <span style={{ fontSize: 11, color: "#37474F" }}>{msg.time}</span>
          {isUser && <span style={{ fontSize: 11, color: "#455A64", fontStyle: "italic" }}>Enviado</span>}
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const { data: session } = useSession();
  const googleAccessToken = (session?.user as any)?.googleAccessToken as string | undefined;

  const [messages, setMessages] = useState<(Message & { typing?: boolean })[]>([
    { id: 0, role: "assistant", content: "Buenos días. Soy SARA, su asistente con memoria persistente. ¿En qué puedo asistirle hoy?", device: "system", time: getTime() },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setActive(true);
    const userMsg: Message = { id: Date.now(), role: "user", content: text, device: "web", time: getTime() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    const thinkingId = Date.now() + 1;
    setMessages(prev => [...prev, { id: thinkingId, role: "assistant", content: "", device: "system", time: "", typing: true }]);
    try {
      const data = await sendChat(text, SESSION_ID, "web", googleAccessToken);
      setMessages(prev => prev.map(m =>
        m.id === thinkingId ? { ...m, content: data.response, typing: false, device: "web", time: getTime() } : m
      ));
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === thinkingId ? { ...m, content: "Error al conectar con el backend.", typing: false, device: "system", time: getTime() } : m
      ));
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar />

      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0, background: "#1A1C1E" }}>

        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "22px 40px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%",
              background: "#1E2427", border: "1px solid #455A64",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: "#78909C" }}>S</span>
            </div>
            <div>
              <p style={{ fontSize: 16, fontWeight: 600, color: "#ECEFF1" }}>SARA</p>
              <div style={{ display: "flex", alignItems: "center", gap: 7, marginTop: 4 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: active ? "#4CAF50" : "#37474F",
                  boxShadow: active ? "0 0 6px rgba(76,175,80,0.5)" : "none",
                }} />
                <span style={{ fontSize: 11, color: "#455A64", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {active ? "Active · lamda94" : "En espera · lamda94"}
                </span>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {[Search, MoreVertical].map((Icon, i) => (
              <button key={i} style={{
                width: 36, height: 36, borderRadius: 9,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#455A64", background: "transparent", border: "none", cursor: "pointer",
              }}>
                <Icon size={15} strokeWidth={1.8} />
              </button>
            ))}
          </div>
        </div>

        {/* Mensajes */}
        <div style={{ flex: 1, overflowY: "auto", padding: "36px 40px", display: "flex", flexDirection: "column", gap: 24 }}>
          <div style={{ textAlign: "center", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.15em", color: "#37474F", marginBottom: 8 }}>
            {getDateLabel()}
          </div>
          {messages.map(msg => <Bubble key={msg.id} msg={msg} />)}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{
          padding: "20px 40px 28px",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          background: "#161819",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 14 }}>
            <div style={{
              flex: 1, display: "flex", alignItems: "flex-end", gap: 12,
              padding: "14px 20px",
              borderRadius: 14,
              background: "#1E2427",
              border: "1px solid rgba(255,255,255,0.06)",
            }}>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Escribe tus pensamientos..."
                rows={1}
                disabled={loading}
                style={{
                  flex: 1, background: "transparent", border: "none", outline: "none",
                  resize: "none", fontSize: 14, color: "#ECEFF1",
                  fontFamily: "inherit", lineHeight: 1.6, maxHeight: 120,
                  scrollbarWidth: "none",
                }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0, paddingBottom: 2 }}>
                {[Smile, Mic].map((Icon, i) => (
                  <button key={i} style={{ color: "#455A64", background: "none", border: "none", cursor: "pointer" }}>
                    <Icon size={17} strokeWidth={1.8} />
                  </button>
                ))}
              </div>
            </div>
            <button onClick={send} disabled={!input.trim() || loading} style={{
              width: 46, height: 46, borderRadius: 13,
              display: "flex", alignItems: "center", justifyContent: "center",
              background: input.trim() && !loading ? "#455A64" : "#1E2427",
              color: input.trim() && !loading ? "#ECEFF1" : "#37474F",
              border: "1px solid rgba(255,255,255,0.06)",
              cursor: input.trim() && !loading ? "pointer" : "default",
              flexShrink: 0, transition: "all 0.15s",
            }}>
              <Send size={16} strokeWidth={2} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
