# SARA — Sistema de Asistencia con Reconocimiento Adaptativo

Asistente virtual con **conciencia y memoria únicas**, compartidas en tiempo real entre todas las instancias (móvil, escritorio, web). Cada interacción desde cualquier dispositivo enriquece el mismo núcleo de conocimiento — al estilo Jarvis de Iron Man.

```
[Móvil]    ──┐
[Desktop]  ──┼──► [FastAPI] ──► [Mem0 + Qdrant] ──► Misma conciencia
[Web]      ──┘         │
                  [PostgreSQL]
                  [Knowledge Graph]
```

---

## Stack

| Capa | Tecnología |
|---|---|
| LLM | Groq API (`llama-3.1-8b-instant`) |
| Backend | Python · FastAPI |
| Memoria | Mem0 (hechos atómicos) + Qdrant (vectores) |
| Knowledge Graph | PostgreSQL + Qdrant (`sara_knowledge`) |
| Base de datos | PostgreSQL |
| Embeddings | Ollama (`nomic-embed-text`, 768 dims) |
| Desktop | Electron · React · Vite |
| Móvil | Flutter (Android) |
| Web | Next.js 15 · TailwindCSS |
| Notificaciones | Firebase Cloud Messaging (FCM) |
| Tunnel | Cloudflare (`api.luismendezdev.online`) |

---

## Estado del proyecto

### FASE 1 — Core Backend ✅
- FastAPI con CORS, health check y logging
- PostgreSQL con SQLAlchemy async
- Qdrant para vectores de memoria (`sara_memories`)
- Ollama + `nomic-embed-text` para embeddings
- Groq como LLM principal
- CLI de prueba (`cli.py`)

### FASE 2 — API + Interfaces Base ✅
- Endpoints: `POST /chat`, `GET /memory/{user_id}`, `GET /health`
- App Desktop Electron + React con `Ctrl+Space` y bandeja del sistema
- App Web Next.js con páginas: Chat, Memoria, Grafo, Archivos, Ajustes
- Cloudflare Tunnel para acceso externo

### FASE 3 — App Móvil ✅
- Flutter (Android) con paleta Nocturne Slate
- Pantallas: `ChatScreen`, `MemoryScreen`
- Push notifications con Firebase Cloud Messaging
- **Modo offline + sync**: SQLite local (`sqflite`) + cola de sincronización automática al reconectar (`connectivity_plus`)

### FASE 4 — Conciencia Avanzada ⚠️ En progreso

#### 4.1 Knowledge Graph ✅
- Nodos y aristas en PostgreSQL (`kg_nodes`, `kg_edges`)
- Embeddings de nodos en Qdrant (`sara_knowledge`)
- Extracción automática de entidades y relaciones con Groq tras cada conversación
- Búsqueda semántica de nodos relacionados inyectada en el system prompt
- Visualización force-directed en SVG en la app web (`/knowledge`)

#### 4.2 Consolidación Automática ⚠️ Parcial
- `POST /agents/consolidate` — fusión manual de memorias similares (threshold 0.88)
- Cron nocturno automático ❌
- Resumen del día ❌

#### 4.3 Perfil Evolutivo del Usuario ✅
- Tabla `user_profiles` en PostgreSQL
- Se regenera automáticamente cada 10 conversaciones en background
- Usa hechos de Mem0 como fuente
- Inyectado en cada system prompt (primacy effect)
- `GET /agents/profile/{session_id}` · `POST /agents/profile/refresh`

#### 4.4 Agentes Especializados ⚠️ Parcial

| Agente | Estado |
|---|---|
| WebSearchAgent (DuckDuckGo) | ✅ |
| ReminderAgent (intent detection + DB) | ✅ |
| CalendarAgent | ❌ |
| CodeAgent | ❌ |
| FileAgent | ❌ |
| EmailAgent | ❌ |

### FASE 5 — Modo Jarvis ❌ Pendiente
- Voz bidireccional: wake word "Hey Sara" + STT (Whisper) + TTS
- Proactividad: resumen matutino, alertas de patrones, recordatorios inteligentes
- Integración con SO: notificaciones, apps, GPS
- HUD visual overlay
- Seguridad: cifrado AES-256, modo privado, auditoría

---

## Arquitectura de memoria

```
Conversación
     │
     ├──► Mem0 (background)
     │    └── Groq extrae hechos atómicos → Qdrant (sara_mem0)
     │
     ├──► Knowledge Graph (background)
     │    └── Groq extrae entidades/relaciones → PostgreSQL + Qdrant (sara_knowledge)
     │
     └──► Perfil evolutivo (cada 10 conversaciones)
          └── Groq analiza hechos → PostgreSQL (user_profiles)

En cada respuesta:
  system prompt = base + perfil + hechos Mem0 + tripletas KG + contexto acción
```

---

## Recordatorios (sin LLM)

Intent detection por keywords → acción directa en DB → respuesta directa

| Intent | Palabras clave |
|---|---|
| `create_reminder` | "recuérdame", "agrega recordatorio", "crea una nota"... |
| `modify_reminder` | "modifica", "cambia", "actualiza el recordatorio"... |
| `delete_reminders` | "elimina", "borra", "cancela los recordatorios"... |
| `list_reminders` | "qué recordatorios", "mis recordatorios", "hoy", "mañana"... |

Notificaciones push via FCM cuando el recordatorio vence (APScheduler cada 30s).

---

## Levantar el stack

```bash
# Requisitos: Docker, Python 3.11+, Flutter, Node 18+, Ollama

# 1. Servicios de infraestructura
docker compose up -d   # PostgreSQL + Qdrant

# 2. Modelos locales
ollama pull nomic-embed-text

# 3. Backend
cd backend
cp .env.example .env   # configurar GROQ_API_KEY y DATABASE_URL
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Tunnel (acceso externo)
cloudflared tunnel run sara-api

# 5. Web
cd clients/web && npm install && npm run dev

# 6. Desktop
cd clients/desktop && npm install && npm run dev

# 7. Móvil
cd clients/sara_mobile && flutter run
```

O todo junto:
```bash
./start.sh
```

---

## Variables de entorno (backend/.env)

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/sara_db
OLLAMA_HOST=http://localhost:11434
EMBED_MODEL=nomic-embed-text
QDRANT_HOST=localhost
QDRANT_PORT=6333
FIREBASE_CREDENTIALS_PATH=/ruta/a/firebase-credentials.json
MEM0_API_KEY=          # vacío = modo local, definido = Mem0 cloud
```

---

## Endpoints principales

```
POST   /chat                          Conversación principal
GET    /memory/{session_id}           Hechos atómicos del usuario (Mem0)
GET    /memory/{session_id}/search    Búsqueda semántica en memoria
GET    /knowledge/{session_id}        Grafo de conocimiento (nodos + aristas)
GET    /agents/profile/{session_id}   Perfil evolutivo actual
POST   /agents/profile/refresh        Regenerar perfil inmediatamente
POST   /agents/consolidate            Fusionar memorias similares
POST   /notifications/register-token  Registrar token FCM
GET    /health                        Estado del servidor
```

---

## Session IDs

| Cliente | Session ID |
|---|---|
| Desktop | `lamda94-desktop` |
| Web | `lamda94-web` |
| Móvil | `lamda94-mobile` |
| CLI | `lamda94-cli` |

Los mensajes con `lamda94` en el session_id activan el `SYSTEM_CREATOR` (trato formal, "señor").

---

## Notas técnicas

- `llama-3.3-70b-versatile` no funciona con tool use en Groq (genera XML inválido) — usar siempre `llama-3.1-8b-instant`
- `firebase-admin` requiere `httpx==0.27.2`
- Mem0 en modo local no necesita API key — usa Groq + Ollama + Qdrant propios
- Para migrar a Mem0 cloud: añadir `MEM0_API_KEY=m0-...` al `.env` y reiniciar
