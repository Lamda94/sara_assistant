"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useSession } from "next-auth/react";
import { Search, MoreVertical, Send, Mic, MicOff, Volume2, VolumeX, Smile } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import { sendChat, getTime, getDateLabel, type Message } from "@/lib/api";

const SESSION_ID = "lamda94-web";
const SILENCE_THRESHOLD = 10;
const SILENCE_TIMEOUT_MS = 1500;

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
  const [isListening, setIsListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const silenceTimerRef = useRef(0);
  const silenceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceEnabledRef = useRef(voiceEnabled);
  const sendRef = useRef<(text: string) => void>(() => {});

  useEffect(() => { voiceEnabledRef.current = voiceEnabled; }, [voiceEnabled]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // ── TTS Playback ──────────────────────────────────────────────

  const stopAudio = useCallback(() => {
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
  }, []);

  const speak = useCallback(async (text: string) => {
    if (!voiceEnabledRef.current || !text) return;
    stopAudio();
    try {
      const res = await fetch("/api/voice/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      currentAudioRef.current = audio;
      audio.onended = () => { URL.revokeObjectURL(url); currentAudioRef.current = null; };
      audio.play().catch(() => {});
    } catch {
      // TTS failed silently
    }
  }, [stopAudio]);

  // ── Send Message ──────────────────────────────────────────────

  const send = async (overrideText?: string) => {
    const text = (overrideText ?? input).trim();
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
      if (voiceEnabledRef.current && data.response) speak(data.response);
    } catch {
      setMessages(prev => prev.map(m =>
        m.id === thinkingId ? { ...m, content: "Error al conectar con el backend.", typing: false, device: "system", time: getTime() } : m
      ));
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  // Keep ref in sync so recorder callback can call send without stale closure
  useEffect(() => { sendRef.current = send; });

  // ── Voice Recording (STT) ─────────────────────────────────────

  const stopRecording = useCallback(() => {
    if (silenceIntervalRef.current) {
      clearInterval(silenceIntervalRef.current);
      silenceIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setIsListening(false);
  }, []);

  const startRecording = useCallback(async () => {
    stopAudio();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimes = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/webm"];
      let mime = "";
      for (const m of mimes) {
        if (MediaRecorder.isTypeSupported(m)) { mime = m; break; }
      }

      const recorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      recorder.onstop = () => {
        const ext = mime.includes("ogg") ? "ogg" : "webm";
        const blob = new Blob(chunks, { type: mime || "audio/webm" });
        if (blob.size < 500) return;
        const form = new FormData();
        form.append("audio", blob, `audio.${ext}`);
        fetch("/api/voice/stt", { method: "POST", body: form })
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data?.text?.trim()) sendRef.current(data.text.trim());
          })
          .catch(() => {});
      };

      // Silence detection
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      silenceTimerRef.current = 0;

      silenceIntervalRef.current = setInterval(() => {
        analyser.getByteFrequencyData(dataArray);
        const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        if (avg < SILENCE_THRESHOLD) {
          silenceTimerRef.current += 100;
          if (silenceTimerRef.current >= SILENCE_TIMEOUT_MS) {
            stopRecording();
          }
        } else {
          silenceTimerRef.current = 0;
        }
      }, 100);

      recorder.start(200);
      setIsListening(true);
    } catch {
      setIsListening(false);
    }
  }, [stopAudio, stopRecording]);

  const toggleListen = useCallback(() => {
    if (isListening) stopRecording();
    else startRecording();
  }, [isListening, stopRecording, startRecording]);

  // ── Keyboard shortcut Ctrl+M ──────────────────────────────────

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "m") { e.preventDefault(); toggleListen(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleListen]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const toggleVoice = () => {
    setVoiceEnabled(prev => {
      if (prev) stopAudio();
      return !prev;
    });
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
                  background: isListening ? "#EF5350" : active ? "#4CAF50" : "#37474F",
                  boxShadow: isListening ? "0 0 8px rgba(239,83,80,0.6)" : active ? "0 0 6px rgba(76,175,80,0.5)" : "none",
                }} />
                <span style={{ fontSize: 11, color: isListening ? "#EF5350" : "#455A64", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                  {isListening ? "Escuchando..." : active ? "Active · lamda94" : "En espera · lamda94"}
                </span>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            <button onClick={toggleVoice} title={voiceEnabled ? "Silenciar voz" : "Activar voz"} style={{
              width: 36, height: 36, borderRadius: 9,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: voiceEnabled ? "#78909C" : "#37474F",
              background: "transparent", border: "none", cursor: "pointer",
            }}>
              {voiceEnabled ? <Volume2 size={15} strokeWidth={1.8} /> : <VolumeX size={15} strokeWidth={1.8} />}
            </button>
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
              border: `1px solid ${isListening ? "rgba(239,83,80,0.3)" : "rgba(255,255,255,0.06)"}`,
              transition: "border-color 0.15s",
            }}>
              <textarea
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder={isListening ? "Escuchando..." : "Escribe tus pensamientos..."}
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
                <button style={{ color: "#455A64", background: "none", border: "none", cursor: "pointer" }}>
                  <Smile size={17} strokeWidth={1.8} />
                </button>
                <button
                  onClick={toggleListen}
                  title={isListening ? "Parar grabación" : "Grabar voz (Ctrl+M)"}
                  style={{
                    background: isListening ? "rgba(183,28,28,0.2)" : "none",
                    border: "none", cursor: "pointer",
                    color: isListening ? "#EF5350" : "#455A64",
                    borderRadius: 6, padding: 2,
                    transition: "all 0.15s",
                  }}
                >
                  {isListening ? <MicOff size={17} strokeWidth={1.8} /> : <Mic size={17} strokeWidth={1.8} />}
                </button>
              </div>
            </div>
            <button onClick={() => send()} disabled={!input.trim() || loading} style={{
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
