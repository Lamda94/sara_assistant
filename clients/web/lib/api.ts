const BASE = "/api";

export interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  device: string;
  time: string;
}

const SESSION_ID = "lamda94-web";

export interface Memory {
  id: string;
  content: string;
}

export async function sendChat(message: string, sessionId: string, device = "web") {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, device }),
  });
  if (!res.ok) throw new Error("Error en el backend");
  return res.json() as Promise<{ response: string; session_id: string }>;
}

export async function getMemories(): Promise<{ total: number; memories: Memory[] }> {
  const res = await fetch(`${BASE}/memory/${SESSION_ID}`);
  if (!res.ok) throw new Error("Error obteniendo memoria");
  const data = await res.json();
  const memories: Memory[] = (data.facts ?? []).map((f: { id: string; memory: string }) => ({
    id: f.id,
    content: f.memory,
  }));
  return { total: data.total ?? memories.length, memories };
}

export async function searchMemories(q: string): Promise<{ query: string; results: Memory[] }> {
  const res = await fetch(`${BASE}/memory/${SESSION_ID}/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error("Error en búsqueda");
  const data = await res.json();
  const results: Memory[] = (data.results ?? []).map((content: string, i: number) => ({
    id: `search-${i}`,
    content,
  }));
  return { query: q, results };
}

export function getTime() {
  return new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
}

export function getDateLabel() {
  return new Date()
    .toLocaleDateString("es", { weekday: "long", month: "long", day: "numeric" })
    .toUpperCase();
}
