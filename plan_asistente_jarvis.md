# Plan de Trabajo: Asistente Virtual Multiplataforma
## "SARA" — Sistema de Asistencia con Reconocimiento Adaptativo
**Conciencia Única · Mobile + Desktop + Web · Básico → Avanzado**

---

## Visión del Proyecto

Construir un asistente virtual con **conciencia y memoria únicas**, compartidas en tiempo real entre todas las instancias (móvil, escritorio, web). Cada interacción desde cualquier dispositivo enriquece el mismo núcleo de conocimiento, logrando que el asistente "recuerde" sin importar desde dónde se le hable — al estilo Jarvis de Iron Man.

---

## Principio de Conciencia Única

El secreto central del proyecto: **no existe memoria por dispositivo**, existe una sola memoria global compartida.

```
[Dispositivo A - Móvil]  ──┐
[Dispositivo B - Desktop] ──┼──► [API Core] ──► [Memory Engine] ──► [Qdrant / Vector DB]
[Dispositivo C - Web]    ──┘                          │
                                                       ▼
                                              Misma conciencia,
                                            sin importar el origen
```

Cuando el usuario pregunta algo desde el móvil, se generan embeddings y se indexan en la base de datos vectorial global. Cuando luego pregunta desde el escritorio, el sistema recupera exactamente el mismo contexto. La identidad del asistente es una sola.

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTES                             │
│  [App Móvil]     [App Desktop]     [App Web]                │
│  React Native    Electron+React    Next.js                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS / WebSockets
┌────────────────────────▼────────────────────────────────────┐
│                     API GATEWAY                             │
│              FastAPI · JWT Auth · Rate Limit                │
└──────┬─────────────────┬──────────────────┬────────────────┘
       │                 │                  │
┌──────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
│  AI Engine  │  │  Memory Mgr  │  │  Agent Layer │
│ Claude API  │  │  Embeddings  │  │  Tools/APIs  │
└─────────────┘  └───────┬──────┘  └─────────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         [Qdrant]  [PostgreSQL]  [Redis]
         Vectores  Conversac.   Caché/RT
```

---

## Stack Tecnológico

| Capa               | Tecnología                        | Justificación                          |
|--------------------|-----------------------------------|----------------------------------------|
| LLM / AI           | Claude API (Anthropic)            | Mejor razonamiento y contexto largo    |
| Backend            | Python · FastAPI                  | Rápido, async, ideal para AI           |
| Memoria vectorial  | Qdrant                            | Búsqueda semántica eficiente           |
| Base de datos      | PostgreSQL                        | Conversaciones, usuarios, metadata     |
| Caché / RT         | Redis                             | Sesiones activas y streaming           |
| Desktop            | Electron · React                  | Multiplataforma nativo                 |
| Móvil              | React Native · Expo               | iOS y Android desde un solo código     |
| Web                | Next.js                           | SSR, performance, SEO                  |
| Voz STT            | Whisper (OpenAI / local)          | Reconocimiento offline                 |
| Voz TTS            | Coqui TTS / ElevenLabs            | Voz personalizada                      |
| Tiempo real        | WebSockets / Socket.io            | Streaming de respuestas                |
| Autenticación      | JWT · OAuth2                      | Sesión única entre plataformas         |

---

## FASE 1 — Fundamentos del Core
**Duración estimada: 3 semanas**
> El cerebro existe antes que el cuerpo.

### Objetivos
Construir el núcleo del sistema: servidor, base de datos, sistema de memoria y prueba de concepto por CLI.

### 1.1 Estructura del Proyecto

```
sara/
├── backend/
│   ├── app/
│   │   ├── main.py              # Entrada FastAPI
│   │   ├── config.py            # Variables de entorno
│   │   ├── routers/
│   │   │   ├── chat.py          # Endpoints de conversación
│   │   │   ├── memory.py        # Endpoints de memoria
│   │   │   └── auth.py          # Autenticación
│   │   ├── services/
│   │   │   ├── ai_service.py    # Integración Claude API
│   │   │   ├── memory_service.py # Gestión de memoria vectorial
│   │   │   └── embedding_service.py # Generación de embeddings
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   └── memory.py
│   │   └── db/
│   │       ├── postgres.py
│   │       └── qdrant.py
│   ├── requirements.txt
│   └── .env
├── clients/
│   ├── desktop/                 # Electron + React
│   ├── mobile/                  # React Native
│   └── web/                     # Next.js
└── docs/
    └── plan_asistente_jarvis.md # Este documento
```

### 1.2 Backend — Servidor FastAPI

**Tareas:**
- [ ] Inicializar proyecto FastAPI con estructura modular
- [ ] Configurar variables de entorno (.env) para API keys y conexiones
- [ ] Implementar middleware CORS para aceptar peticiones de todos los clientes
- [ ] Endpoint `GET /health` para verificar estado del servidor
- [ ] Logging estructurado con contexto de dispositivo origen

### 1.3 Base de Datos PostgreSQL

**Tablas iniciales:**
```sql
users            -- id, nombre, email, created_at
conversations    -- id, user_id, device_origin, started_at
messages         -- id, conversation_id, role, content, timestamp
memory_entries   -- id, user_id, content, importance_score, last_accessed
```

**Tareas:**
- [ ] Configurar PostgreSQL con Docker
- [ ] Crear esquema inicial con migraciones (Alembic)
- [ ] Modelos SQLAlchemy para cada tabla
- [ ] CRUD básico para usuarios y conversaciones

### 1.4 Sistema de Memoria Compartida (Conciencia Única)

Este es el módulo más crítico del proyecto.

**Flujo de memoria:**
```
Usuario envía mensaje
        │
        ▼
Generar embedding del mensaje (text-embedding-3-small o similar)
        │
        ▼
Buscar en Qdrant los N recuerdos más similares (cosine similarity)
        │
        ▼
Inyectar recuerdos relevantes como contexto al prompt de Claude
        │
        ▼
Claude genera respuesta con contexto enriquecido
        │
        ▼
Guardar mensaje + respuesta como nuevo recuerdo en Qdrant
        │
        ▼
Actualizar metadata en PostgreSQL (cuándo, desde qué dispositivo)
```

**Tareas:**
- [ ] Configurar Qdrant con Docker (colección `sara_memories`)
- [ ] Módulo `EmbeddingService`: genera vectores de texto
- [ ] Módulo `MemoryService`:
  - `store(content, user_id, device, importance)` — guarda recuerdo
  - `retrieve(query, user_id, top_k=5)` — recupera recuerdos relevantes
  - `consolidate()` — fusiona recuerdos duplicados o relacionados
- [ ] Política de importancia: no todos los recuerdos tienen el mismo peso

### 1.5 Integración Claude API

**Tareas:**
- [ ] Módulo `AIService` que gestiona llamadas a Claude
- [ ] System prompt base que define la personalidad del asistente
- [ ] Inyección dinámica de memoria relevante en cada prompt
- [ ] Soporte para streaming de respuestas (chunks)
- [ ] Manejo de errores y reintentos

### 1.6 Cliente CLI (Validación)

**Tareas:**
- [ ] Script `cli.py` para conversar con el backend por terminal
- [ ] Verificar que la memoria persiste entre sesiones distintas
- [ ] Verificar que simular dos "dispositivos" distintos comparte el mismo contexto

**Entregable de Fase 1:** Backend funcional con memoria vectorial operativa, validado por CLI.

---

## FASE 2 — API REST Completa + Interfaces Base
**Duración estimada: 4 semanas**
> El cuerpo toma forma.

### 2.1 API REST Completa

**Endpoints:**
```
POST   /auth/register          Registro de usuario
POST   /auth/login             Login, retorna JWT
POST   /chat                   Enviar mensaje, retorna respuesta
GET    /chat/history           Historial de conversación
GET    /memory                 Ver recuerdos activos del usuario
POST   /memory/consolidate     Fusionar y limpiar recuerdos
DELETE /memory/{id}            Eliminar un recuerdo específico
GET    /context                Estado actual del asistente para ese usuario
WS     /ws/chat                WebSocket para streaming en tiempo real
```

**Tareas:**
- [ ] Implementar todos los endpoints con validación Pydantic
- [ ] Autenticación JWT en todos los endpoints protegidos
- [ ] Rate limiting por usuario y por dispositivo
- [ ] Documentación automática con Swagger (FastAPI lo genera solo)
- [ ] Tests unitarios para cada endpoint

### 2.2 App Desktop — Electron + React

**Características:**
- Ventana flotante siempre visible (modo HUD)
- Input combinado: texto + botón de voz
- Historial de conversación con scroll infinito
- Indicador de origen: "Este recuerdo viene de tu móvil"
- Modo compacto / expandido

**Tareas:**
- [ ] Inicializar proyecto Electron + React + Vite
- [ ] Componente `ChatWindow` con historial y input
- [ ] Integración con WebSocket del backend (respuestas en streaming)
- [ ] Almacenamiento local de sesión (token JWT)
- [ ] Auto-start con el sistema operativo
- [ ] Atajos de teclado globales para abrir/cerrar

### 2.3 App Web — Next.js

**Características:**
- Dashboard principal de conversación
- Panel lateral con memoria activa visualizada
- Configuración del asistente (nombre, tono, personalidad)
- Historial completo con búsqueda

**Tareas:**
- [ ] Inicializar proyecto Next.js con App Router
- [ ] Páginas: `/` (chat), `/memory` (recuerdos), `/settings`
- [ ] Componentes reutilizables: `ChatBubble`, `MemoryCard`, `DeviceBadge`
- [ ] Autenticación con cookies HTTPOnly
- [ ] Diseño oscuro futurista (estilo Jarvis)

**Entregable de Fase 2:** Backend completo + Desktop + Web funcionales y conectados.

---

## FASE 3 — App Móvil
**Duración estimada: 4 semanas**
> La conciencia llega al bolsillo.

### 3.1 React Native + Expo

**Características:**
- Interfaz de chat optimizada para touch
- Reconocimiento de voz con Whisper (puede funcionar offline)
- Notificaciones push (el asistente puede iniciar contacto)
- Modo sin conexión con sincronización posterior

**Tareas:**
- [ ] Inicializar proyecto Expo con TypeScript
- [ ] Pantallas: `Chat`, `Memory`, `Settings`, `Login`
- [ ] Integración con API backend usando Axios + interceptores JWT
- [ ] Módulo de voz: grabación, transcripción con Whisper, envío
- [ ] Push notifications con Expo Notifications
- [ ] SQLite local para modo offline

### 3.2 Sincronización Offline

**Flujo:**
```
Sin conexión → mensajes guardados en SQLite local
Reconecta    → sincroniza mensajes pendientes al backend
Backend      → genera embeddings de lo que faltaba y actualiza Qdrant
Resultado    → conciencia al día en todos los dispositivos
```

**Tareas:**
- [ ] Cola de sincronización con manejo de conflictos
- [ ] Indicador visual de estado de sync
- [ ] Resolución automática de duplicados

**Entregable de Fase 3:** Las tres plataformas funcionan con conciencia compartida en tiempo real.

---

## FASE 4 — Conciencia Avanzada
**Duración estimada: 5 semanas**
> El asistente empieza a "pensar".

### 4.1 Knowledge Graph

Las memorias no son puntos aislados, son nodos conectados.

**Estructura:**
```
[Proyecto "Sara"] ──relacionado con──► [Python]
[Python] ──usado en──► [FastAPI]
[FastAPI] ──mencionado──► [Conversación del 2026-03-27]
```

**Tareas:**
- [ ] Integrar Neo4j o usar Qdrant con payloads relacionales
- [ ] Módulo `KnowledgeGraph`: crear, conectar y consultar nodos
- [ ] Al recuperar memoria, incluir nodos relacionados en el contexto
- [ ] Visualización del grafo en la app web

### 4.2 Consolidación Automática

**Tareas:**
- [ ] Job nocturno (cron) que analiza recuerdos del día
- [ ] Fusiona recuerdos similares en uno más rico
- [ ] Calcula y actualiza scores de importancia
- [ ] Elimina recuerdos de baja importancia y antiguos
- [ ] Genera un "resumen del día" que se guarda como memoria especial

### 4.3 Perfil Evolutivo del Usuario

**Tareas:**
- [ ] Módulo `UserProfile`: extrae preferencias de las conversaciones
- [ ] Detecta: horarios activos, temas frecuentes, estilo de comunicación
- [ ] El system prompt se personaliza dinámicamente con este perfil
- [ ] Panel en web para ver y editar el perfil detectado

### 4.4 Agentes Especializados

Cada agente es una herramienta que Claude puede decidir usar:

| Agente          | Función                                           |
|-----------------|---------------------------------------------------|
| WebSearchAgent  | Busca información actualizada en internet         |
| CalendarAgent   | Lee y escribe en Google Calendar                  |
| CodeAgent       | Genera, explica y depura código                   |
| FileAgent       | Lee y organiza archivos locales del usuario       |
| ReminderAgent   | Gestiona recordatorios y alertas                  |
| EmailAgent      | Resume y redacta correos                          |

**Tareas:**
- [ ] Framework de agentes con interfaz común `BaseAgent`
- [ ] Integrar agentes como tools en las llamadas a Claude API
- [ ] El asistente decide qué agente usar según el contexto
- [ ] Logging de qué agente usó en cada respuesta

**Entregable de Fase 4:** Asistente con conocimiento conectado, perfil de usuario y capacidad de usar herramientas externas.

---

## FASE 5 — Modo Jarvis
**Duración estimada: 6 semanas**
> El asistente toma iniciativa.

### 5.1 Voz Bidireccional Completa

**Tareas:**
- [ ] Wake word detection: "Hey Sara" en desktop y móvil
- [ ] Pipeline de voz: Wake word → STT (Whisper) → LLM → TTS → Audio
- [ ] Voz personalizada con Coqui TTS entrenada o ElevenLabs
- [ ] Modo conversación continua sin botones
- [ ] Detección de fin de frase para envío automático

### 5.2 Proactividad

El asistente no solo responde, también inicia.

**Tareas:**
- [ ] Motor de proactividad basado en contexto del usuario
- [ ] Recordatorios inteligentes: "Dijiste que ibas a terminar X hoy"
- [ ] Resumen matutino automático al primer uso del día
- [ ] Alertas de patrones: "Llevas 3 días sin avanzar en Y"
- [ ] Sugerencias no intrusivas basadas en memoria activa

### 5.3 Integración con el Sistema Operativo

**Desktop:**
- [ ] Leer notificaciones del sistema (via APIs nativas)
- [ ] Abrir aplicaciones por comando de voz
- [ ] Capturar pantalla y analizarla (modo "¿qué estoy viendo?")
- [ ] Control básico del sistema: volumen, brillo, modo no molestar

**Móvil:**
- [ ] Leer notificaciones con permiso del usuario
- [ ] Acceso a contactos para enviar mensajes
- [ ] Integración con GPS para contexto de ubicación

### 5.4 HUD Visual (Fase Avanzada Opcional)

**Tareas:**
- [ ] Overlay transparente siempre encima (Electron window sin bordes)
- [ ] Animaciones de "procesamiento" mientras el asistente piensa
- [ ] Visualización de recuerdos activos como burbujas flotantes
- [ ] Modo presentación: muestra datos relevantes en pantalla grande
- [ ] Tema personalizable (colores, opacidad, posición)

### 5.5 Seguridad y Privacidad

**Tareas:**
- [ ] Cifrado de memoria en reposo (AES-256)
- [ ] Opción de memoria local sin sincronización a la nube
- [ ] Control granular: qué se recuerda y qué se olvida
- [ ] Modo privado: sesiones que no dejan recuerdo
- [ ] Auditoría de accesos a la memoria

**Entregable de Fase 5:** Asistente completo, proactivo, con voz y control del entorno.

---

## FASE 6 — Inteligencia Evolutiva
**Duración estimada: 5 semanas**
> SARA deja de ser un chatbot y empieza a pensar.

### 6.1 Procesamiento Nocturno (La Madrugada)

SARA usa las horas de inactividad (2am–6am) para analizar, aprender y evolucionar.

**Tareas:**
- [ ] Job nocturno de **autoevaluación**: revisar conversaciones del día, detectar respuestas robóticas, imprecisas o donde no entendió la intención
- [ ] **Síntesis de patrones**: cruzar datos de memoria para generar observaciones ("el usuario mencionó estrés laboral 3 veces esta semana", "lleva 5 días sin preguntar por su proyecto X")
- [ ] **Generación de temas proactivos**: preparar conversaciones naturales basadas en contexto acumulado, no solo responder
- [ ] **Refinamiento del perfil de personalidad**: ajustar nivel de formalidad, humor, empatía según las interacciones recientes
- [ ] **Reporte de evolución**: log semanal de qué aprendió, qué mejoró y qué falló

### 6.2 Personalidad Adaptativa

El system prompt deja de ser estático y se enriquece dinámicamente.

**Tareas:**
- [ ] **Brief de personalidad**: documento generado cada noche con el tono, estilo y temas relevantes para el usuario
- [ ] **Memoria emocional**: detectar y recordar estados emocionales del usuario a lo largo del tiempo (no solo hechos)
- [ ] **Estilo conversacional**: SARA adapta su forma de hablar según el contexto (informal en chat casual, precisa en temas técnicos, empática en momentos difíciles)
- [ ] **Opiniones propias**: SARA desarrolla preferencias y opiniones basadas en lo que ha aprendido del usuario, no solo repite información

### 6.3 Razonamiento Profundo

SARA piensa antes de responder, no solo genera texto.

**Tareas:**
- [ ] **Chain-of-thought interno**: antes de responder, SARA analiza la intención real detrás de la pregunta
- [ ] **Contexto temporal**: SARA entiende cuándo las cosas pasaron y su relevancia actual ("eso fue hace 2 meses, ¿sigue siendo relevante?")
- [ ] **Conexión de puntos**: relacionar información de distintas conversaciones para dar respuestas más completas
- [ ] **Detección de contradicciones**: si el usuario dice algo que contradice lo que dijo antes, SARA lo nota y pregunta

### 6.4 Aprendizaje por Feedback

SARA aprende de sus errores y aciertos.

**Tareas:**
- [ ] **Feedback implícito**: si el usuario reformula la pregunta, SARA entiende que no respondió bien
- [ ] **Feedback explícito**: el usuario puede decir "eso no es lo que quería" y SARA ajusta su enfoque
- [ ] **Registro de aciertos**: cuando el usuario confirma o agradece, SARA refuerza ese patrón de respuesta
- [ ] **Anti-patrones**: lista generada automáticamente de cosas que SARA no debe hacer (basada en correcciones del usuario)

**Entregable de Fase 6:** SARA evoluciona sola cada noche, adapta su personalidad, razona mejor y aprende de sus errores.

---

## Cronograma Resumido

| Fase | Contenido                          | Duración    | Semanas   | Estado      |
|------|------------------------------------|-------------|-----------|-------------|
| 1    | Core Backend + Memoria Vectorial   | 3 semanas   | 1 – 3     | ✅ Completa |
| 2    | API Completa + Desktop + Web       | 4 semanas   | 4 – 7     | ✅ Completa |
| 3    | App Móvil + Sync Offline           | 4 semanas   | 8 – 11    | ✅ Completa |
| 4    | Knowledge Graph + Agentes          | 5 semanas   | 12 – 16   | ✅ Completa |
| 5    | Voz + Proactividad + HUD           | 6 semanas   | 17 – 22   | ✅ Completa |
| 5.5  | Seguridad Backend                  | 1 semana    | —         | ✅ Completa |
| 6    | Inteligencia Evolutiva             | 5 semanas   | 23 – 27   | 📋 Pendiente |

**Total estimado: 27 semanas** (adaptable según ritmo de trabajo)

---

## Métricas de Éxito

- [ ] Una pregunta hecha en móvil es recordada en desktop sin configuración adicional
- [ ] El asistente responde en menos de 2 segundos en modo texto
- [ ] El asistente responde en menos de 4 segundos en modo voz (STT + LLM + TTS)
- [ ] La memoria vectorial recupera recuerdos relevantes con >85% de precisión
- [ ] El sistema opera con múltiples usuarios sin mezclar memorias
- [ ] La app móvil funciona offline y sincroniza sin pérdida de datos

---

## Próximo Paso Inmediato

**Comenzar con Fase 1.1 y 1.2:**
1. Crear estructura de carpetas del proyecto
2. Configurar Docker con PostgreSQL y Qdrant
3. Inicializar servidor FastAPI
4. Implementar el primer endpoint `/chat` conectado a Claude API
5. Implementar `MemoryService` básico con Qdrant

---

*Documento generado: 2026-03-27*
*Proyecto: SARA — Asistente Virtual con Conciencia Única*
