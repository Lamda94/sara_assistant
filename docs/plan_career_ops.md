# Plan de Implementación — Career-Ops en SARA
## Búsqueda de empleo autónoma con modo activo
**Contenedor dedicado + integración como agente de SARA**

---

## 1. Visión General

Integrar el proyecto open-source career-ops (santifer/career-ops) como un contenedor Docker independiente dentro del stack de SARA. El usuario activa un "modo búsqueda de empleo" y SARA escanea portales, evalúa ofertas, genera CVs personalizados y registra toda la actividad automáticamente.

**Principio clave:** El código de career-ops se mantiene tal cual. SARA actúa como interfaz conversacional y el contenedor ejecuta la lógica original.

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    SARA Backend                          │
│                                                          │
│  Usuario: "SARA, activa búsqueda de empleo"             │
│                       │                                  │
│              ┌────────▼────────┐                        │
│              │ CareerOps Agent │                         │
│              │ (bridge/proxy)  │                         │
│              └────────┬────────┘                        │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP interno (sara_net)
┌───────────────────────▼─────────────────────────────────┐
│           sara_career (contenedor)                       │
│                                                          │
│  Node.js 22 + Playwright + Chromium + career-ops         │
│                                                          │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────┐ │
│  │Scanner   │ │Evaluator │ │PDF Gen    │ │Applicator │ │
│  │(portals) │ │(A-F+G)   │ │(CV tailor)│ │(auto-fill)│ │
│  └──────────┘ └──────────┘ └───────────┘ └───────────┘ │
│                       │                                  │
│              ┌────────▼────────┐                        │
│              │  API REST mini  │ ← Express/Fastify       │
│              │  :4000          │                         │
│              └─────────────────┘                        │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
                   PostgreSQL (tablas compartidas)
```

---

## 3. Flujo del Modo Activo

```
1. Usuario: "SARA, activa búsqueda de empleo"
   └──► career_mode = ON en BD

2. Job programado (cada 6h, solo si modo activo):
   ├──► Scanner escanea portales configurados
   │       └──► Nuevas ofertas detectadas
   ├──► Evaluador analiza cada oferta (bloques A-F+G)
   │       └──► Score 1-5 + compatibilidad %
   ├──► Si score >= 4.0 → genera CV personalizado PDF
   │       └──► Guardado en /output
   ├──► Registra en BD:
   │       - Portal, vacante, score, CV, fecha/hora, estado
   └──► Push notification al celular

3. Usuario: "SARA, desactiva búsqueda"
   └──► career_mode = OFF, jobs se detienen
```

---

## 4. Modelo de Datos (PostgreSQL)

### Tabla: `career_profiles` — Perfil profesional
```
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100) UNIQUE
full_name           VARCHAR(200)
email               VARCHAR(254)
phone               VARCHAR(50)
location            VARCHAR(200)
linkedin_url        VARCHAR(500)
portfolio_url       VARCHAR(500)
github_url          VARCHAR(500)
cv_markdown         TEXT                -- CV completo en markdown
target_roles        JSONB               -- ["AI Engineer", "ML Lead"]
archetypes          JSONB               -- arquetipos career-ops
narrative           JSONB               -- headline, superpowers, proof_points
compensation        JSONB               -- {min, max, currency, flexibility}
title_positive      JSONB               -- keywords que buscar
title_negative      JSONB               -- keywords que excluir
career_mode         BOOLEAN DEFAULT FALSE  -- modo activo ON/OFF
scan_interval_hours INT DEFAULT 6
min_score_cv        FLOAT DEFAULT 4.0   -- score mínimo para generar CV
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### Tabla: `career_portals` — Portales configurados
```
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100)
company_name        VARCHAR(200)
careers_url         VARCHAR(500)
api_url             VARCHAR(500) NULL    -- Greenhouse/Ashby/Lever API
ats_provider        VARCHAR(50)          -- greenhouse/ashby/lever/workday/custom
enabled             BOOLEAN DEFAULT TRUE
last_scanned_at     TIMESTAMP NULL
created_at          TIMESTAMP
```

### Tabla: `career_applications` — Registro de cada vacante
```
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100) INDEX
company             VARCHAR(200)
role                VARCHAR(300)
url                 VARCHAR(500)
portal_source       VARCHAR(100)         -- "greenhouse/anthropic"
jd_text             TEXT                 -- job description completa
score               FLOAT                -- 1.0 - 5.0
compatibility_pct   INTEGER              -- 0-100 match CV vs JD
archetype           VARCHAR(100)         -- "AI Platform / LLMOps"
evaluation_blocks   JSONB                -- resultados bloques A-G completos
evaluation_summary  TEXT                 -- resumen legible
cv_path             VARCHAR(500) NULL    -- ruta del PDF generado
cv_changes          JSONB NULL           -- cambios aplicados al CV base
interview_stories   JSONB NULL           -- STAR+R mapeadas
legitimacy          VARCHAR(20)          -- high/caution/suspicious
status              VARCHAR(30)          -- evaluated/cv_generated/applied/interview/offer/rejected/discarded
applied_at          TIMESTAMP NULL
applied_method      VARCHAR(20) NULL     -- "auto" / "manual"
notes               TEXT NULL
created_at          TIMESTAMP
updated_at          TIMESTAMP
```

### Tabla: `career_activity_log` — Registro de cada ciclo
```
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100)
cycle_date          TIMESTAMP
portals_scanned     INTEGER
vacancies_found     INTEGER
vacancies_evaluated INTEGER
vacancies_cv_generated INTEGER
vacancies_applied   INTEGER
top_score           FLOAT NULL
top_company         VARCHAR(200) NULL
top_role            VARCHAR(300) NULL
errors              TEXT NULL
duration_seconds    FLOAT
created_at          TIMESTAMP
```

### Tabla: `career_scan_history` — Dedup de URLs
```
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100)
url                 VARCHAR(500) INDEX
company             VARCHAR(200)
title               VARCHAR(300)
portal_source       VARCHAR(100)
status              VARCHAR(30)          -- added/skipped_title/skipped_dup/skipped_expired
first_seen_at       TIMESTAMP
```

---

## 5. Contenedor Docker: `sara_career`

### Dockerfile
```dockerfile
FROM node:22-slim

RUN npx playwright install --with-deps chromium

WORKDIR /career-ops
COPY career-ops/ .
RUN npm ci

COPY career-api/ /career-api
WORKDIR /career-api
RUN npm ci

EXPOSE 4000
CMD ["node", "server.mjs"]
```

### docker-compose.prod.yml (nuevo servicio)
```yaml
sara_career:
  build:
    context: ./career-ops-container
  image: sara_career:latest
  container_name: sara_career
  environment:
    GROQ_API_KEY: ${GROQ_API_KEY}
  volumes:
    - career_output:/career-ops/output
    - career_data:/career-ops/data
  restart: unless-stopped
  networks:
    - sara_net
  deploy:
    resources:
      limits:
        memory: 2g
```

### Impacto en recursos
```
RAM:   +600 MB idle / +1.5 GB escaneando (pico)
Disco: +600 MB (Node.js + Chromium + career-ops)
CPU:   Picos al escanear, mínimo en reposo
Total VPS: ~3.1 GB pico de 11 GB disponibles = OK
```

---

## 6. API REST del contenedor (career-api/server.mjs)

Wrapper Express ligero que expone career-ops como servicio HTTP:

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `POST /scan` | POST | Ejecuta scanner de portales |
| `POST /evaluate` | POST | Evalúa una oferta (URL o texto JD) |
| `POST /generate-cv` | POST | Genera CV personalizado para una evaluación |
| `POST /compare` | POST | Compara múltiples evaluaciones |
| `POST /interview-prep` | POST | Genera prep de entrevista |
| `POST /deep-research` | POST | Investigación profunda de empresa |
| `GET /status` | GET | Estado del contenedor y último ciclo |
| `POST /configure` | POST | Actualizar perfil y portales |

---

## 7. Agente SARA: CareerAgent

### Actions
| Action | Descripción | Ejemplo |
|--------|-------------|---------|
| `activate` | Activa modo búsqueda | "Activa búsqueda de empleo" |
| `deactivate` | Desactiva modo búsqueda | "Desactiva búsqueda" |
| `scan` | Escaneo manual inmediato | "Escanea portales ahora" |
| `evaluate` | Evaluar oferta específica | "Evalúa esta oferta: [url]" |
| `cv` | Generar CV para una oferta | "Genera mi CV para la oferta #42" |
| `status` | Ver estado y actividad reciente | "Cómo van mis aplicaciones?" |
| `prep` | Preparación de entrevista | "Prepárame para la entrevista con Amazon" |
| `profile` | Ver/editar perfil profesional | "Actualiza mi perfil" |
| `portals` | Gestionar portales | "Agrega Anthropic a mis portales" |

---

## 8. Vistas

### Web: `/career`
- **Toggle** modo activo/inactivo
- **Métricas**: último ciclo, ofertas encontradas, CVs generados, aplicaciones
- **Tabla de aplicaciones**: empresa, rol, score, compatibilidad %, CV, estado, fecha
- **Click en fila**: detalle completo (evaluación A-F, cambios CV, JD, post-mortem)
- **Sección portales**: lista de portales configurados con toggle enabled/disabled

### Mobile: `CareerScreen`
- **Card de estado**: modo ON/OFF, último escaneo, stats
- **Lista de aplicaciones** expandible (como SABE)
- **Accesible** desde AppBar del chat

---

## 9. Actividades de Implementación

### Fase 1: Contenedor career-ops
| # | Actividad | Archivos | Estado |
|---|-----------|----------|--------|
| 1.1 | Clonar repo santifer/career-ops en VPS | `/opt/sara/career-ops-container/career-ops/` | ⬜ Pendiente |
| 1.2 | Configurar perfil de usuario (profile.yml, cv.md) | `career-ops/config/profile.yml`, `career-ops/data/cv.md` | ⬜ Pendiente |
| 1.3 | Configurar portales objetivo (portals.yml) | `career-ops/data/portals.yml` | ⬜ Pendiente |
| 1.4 | Crear API wrapper Express (server.mjs) | `career-ops-container/career-api/server.mjs` | ⬜ Pendiente |
| 1.5 | Crear Dockerfile | `career-ops-container/Dockerfile` | ⬜ Pendiente |
| 1.6 | Agregar servicio a docker-compose.prod.yml | `docker-compose.prod.yml` | ⬜ Pendiente |
| 1.7 | Build y verificar que el contenedor levanta | — | ⬜ Pendiente |
| 1.8 | Probar endpoints del API wrapper manualmente | — | ⬜ Pendiente |

### Fase 2: Backend SARA (modelos + agente)
| # | Actividad | Archivos | Estado |
|---|-----------|----------|--------|
| 2.1 | Crear modelos PostgreSQL (5 tablas) | `backend/app/models/career.py` | ⬜ Pendiente |
| 2.2 | Crear CareerAgent (9 actions, bridge al contenedor) | `backend/app/agents/career_agent.py` | ⬜ Pendiente |
| 2.3 | Crear servicio de ciclo automático (job cada 6h) | `backend/app/services/career_service.py` | ⬜ Pendiente |
| 2.4 | Registrar agente en __init__.py | `backend/app/agents/__init__.py` | ⬜ Pendiente |
| 2.5 | Importar modelo en main.py + registrar router | `backend/app/main.py` | ⬜ Pendiente |
| 2.6 | Actualizar system prompt para usar CareerAgent | `backend/app/services/ai_service.py` | ⬜ Pendiente |
| 2.7 | Crear router REST /career/* | `backend/app/routers/career.py` | ⬜ Pendiente |
| 2.8 | Agregar job al scheduler (solo si modo activo) | `backend/app/services/notification_service.py` | ⬜ Pendiente |
| 2.9 | Registrar dispatch del agente (session_id) | `backend/app/services/ai_service.py` | ⬜ Pendiente |

### Fase 3: Vistas
| # | Actividad | Archivos | Estado |
|---|-----------|----------|--------|
| 3.1 | Crear vista web /career (dashboard + tabla + detalle) | `clients/web/app/career/page.tsx` | ⬜ Pendiente |
| 3.2 | Agregar link en Sidebar web | `clients/web/components/Sidebar.tsx` | ⬜ Pendiente |
| 3.3 | Crear CareerScreen mobile (cards + lista expandible) | `clients/sara_mobile/lib/screens/career_screen.dart` | ⬜ Pendiente |
| 3.4 | Agregar botón en AppBar mobile | `clients/sara_mobile/lib/screens/chat_screen.dart` | ⬜ Pendiente |

### Fase 4: Deploy y configuración
| # | Actividad | Archivos | Estado |
|---|-----------|----------|--------|
| 4.1 | Build completo en VPS (todos los contenedores) | — | ⬜ Pendiente |
| 4.2 | Verificar health de sara_career | — | ⬜ Pendiente |
| 4.3 | Configurar perfil profesional del usuario | — | ⬜ Pendiente |
| 4.4 | Configurar portales objetivo | — | ⬜ Pendiente |
| 4.5 | Probar ciclo completo: activar → scan → evaluar → CV | — | ⬜ Pendiente |
| 4.6 | Probar vistas web y mobile | — | ⬜ Pendiente |
| 4.7 | Build e instalar APK en celular | — | ⬜ Pendiente |

### Fase 5: Refinamiento
| # | Actividad | Archivos | Estado |
|---|-----------|----------|--------|
| 5.1 | Auto-aplicación: llenar formularios automáticamente | career-api + apply mode | ⬜ Pendiente |
| 5.2 | Preparación de entrevistas con story bank | career-api + interview-prep mode | ⬜ Pendiente |
| 5.3 | Análisis de patrones de rechazo | career-api + patterns mode | ⬜ Pendiente |
| 5.4 | Daily briefing de CareerOps (integrado con el de SABE) | `backend/app/services/career_service.py` | ⬜ Pendiente |
| 5.5 | Push notifications cuando hay ofertas con score >= 4.5 | `backend/app/services/notification_service.py` | ⬜ Pendiente |

---

## 10. Interacción con SARA

```
"SARA, activa búsqueda de empleo"
→ Activa modo, empieza a escanear cada 6h

"SARA, escanea portales ahora"
→ Ejecuta ciclo manual: scan → evaluate → CV

"SARA, evalúa esta oferta: https://jobs.lever.co/anthropic/..."
→ Evaluación A-F+G en tiempo real, score + compatibilidad

"SARA, genera mi CV para la oferta #12"
→ CV PDF personalizado, optimizado para ATS

"SARA, cómo van mis aplicaciones?"
→ Tabla: 15 evaluadas, 8 CVs generados, 3 aplicadas, 1 entrevista

"SARA, prepárame para la entrevista con Anthropic"
→ Preguntas probables + STAR+R stories + señales de la empresa

"SARA, agrega Microsoft a mis portales"
→ Detecta URL de careers, agrega a portals.yml

"SARA, desactiva búsqueda"
→ Para jobs, mantiene historial
```

---

## 11. Resumen de archivos

### Nuevos (14 archivos)
| Archivo | Descripción |
|---------|-------------|
| `career-ops-container/Dockerfile` | Imagen Docker con Node.js + Playwright + career-ops |
| `career-ops-container/career-ops/` | Clon del repo santifer/career-ops |
| `career-ops-container/career-api/server.mjs` | API wrapper Express |
| `career-ops-container/career-api/package.json` | Dependencias del wrapper |
| `backend/app/models/career.py` | 5 modelos SQLAlchemy |
| `backend/app/agents/career_agent.py` | Agente bridge (9 actions) |
| `backend/app/services/career_service.py` | Ciclo automático + lógica |
| `backend/app/routers/career.py` | Endpoints REST |
| `clients/web/app/career/page.tsx` | Dashboard web |
| `clients/sara_mobile/lib/screens/career_screen.dart` | Pantalla mobile |

### Modificados (6 archivos)
| Archivo | Cambio |
|---------|--------|
| `docker-compose.prod.yml` | +servicio sara_career |
| `backend/app/agents/__init__.py` | +CareerAgent |
| `backend/app/main.py` | +import modelo + router |
| `backend/app/services/ai_service.py` | +system prompt + dispatch |
| `backend/app/services/notification_service.py` | +job cada 6h |
| `clients/web/components/Sidebar.tsx` | +link /career |

---

## 12. Dependencias del usuario

Para que CareerOps funcione, necesito del usuario:

| Dato | Para qué | Cuándo |
|------|----------|--------|
| CV en markdown o PDF | Base para personalizar por oferta | Fase 4.3 |
| Roles objetivo | Qué tipo de posiciones buscar | Fase 4.3 |
| Rango salarial | Filtrar y evaluar compensación | Fase 4.3 |
| Lista de empresas/portales | Dónde escanear | Fase 4.4 |
| Keywords positivos/negativos | Filtrar títulos de ofertas | Fase 4.4 |

---

*Documento generado: 2026-04-17*
*Proyecto: SARA — CareerOps (Búsqueda de empleo autónoma)*
