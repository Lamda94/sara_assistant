# Plan de Implementación — Agente SABE
## Sistema de Análisis de Betting Estratégico
**Agente predictivo multideporte con fase de aprendizaje por simulación**

---

## 1. Visión General

Construir un agente dentro de SARA capaz de ejecutar análisis heurístico y estadístico profundo para identificar "valor" en cuotas deportivas (Value Betting), minimizando el sesgo emocional y maximizando el ROI en cualquier disciplina deportiva.

El agente opera en dos fases:
1. **Fase de Aprendizaje**: Apuestas simuladas (paper betting) con análisis post-mortem automático
2. **Fase Operativa**: Solo se activa cuando alcanza 85% de acierto en las últimas 5 simulaciones

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    FUENTES DE DATOS                      │
│  [Odds API]  [Sports API]  [News/Sentiment]  [Weather]  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              SABE Agent (backend)                        │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐ │
│  │Stats     │ │Market    │ │Prediction  │ │Bankroll  │ │
│  │Engine    │ │Scanner   │ │Model       │ │Manager   │ │
│  └──────────┘ └──────────┘ └────────────┘ └──────────┘ │
│                       │                                  │
│              ┌────────▼────────┐                        │
│              │ Paper Betting   │                         │
│              │ (Simulación)    │                         │
│              └────────┬────────┘                        │
└───────────────────────┼─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   [PostgreSQL]    [Web View]     [Mobile View]
   sim_bets        /betting        BettingScreen
```

---

## 3. Fuentes de Datos (APIs)

| Dato | API | Costo | Cobertura |
|------|-----|-------|-----------|
| Cuotas en vivo | **The Odds API** | Free (500 req/mes) | 40+ bookmakers, múltiples deportes |
| Estadísticas fútbol | **API-Football** | Free (100 req/día) | Fútbol global, H2H, lineups, lesiones |
| NBA/NFL/MLB stats | **API-Sports** | Free tier | Multi-deporte, standings, jugadores |
| Clima | **OpenWeather** | Free | Temperatura, viento, lluvia por ciudad |
| Noticias/Sentimiento | **DuckDuckGo + LLM** | Free | WebSearchAgent existente en SARA |

**Costo total en fase de aprendizaje: $0** (tiers gratuitos suficientes para 3-4 análisis diarios).

---

## 4. Capas de Análisis

### 4.1 Capa de Rendimiento Deportivo (Core Stats)

- **Forma reciente (Momentum)**: Rendimiento en últimos 5, 10 y 20 partidos, no solo histórico general
- **Head-to-Head (H2H)**: Registro entre ambos contendientes, filtrado por relevancia temporal (últimos 2 años pesan más que hace 10)
- **Factor Localía/Visitante**: Rendimiento diferencial por entorno, viajes y presión del público
- **Métricas avanzadas por deporte**:
  - Fútbol: xG (goles esperados), xGA, posesión efectiva
  - NBA: PER, offensive/defensive rating, pace
  - Béisbol: ERA ajustado, WHIP, OPS
  - Tenis: % primer servicio, break points, rendimiento por superficie

### 4.2 Capa de Variables Externas (Hidden Factors)

- **Perfil arbitral**: Tendencia a tarjetas, faltas por partido, sesgo local/visitante
- **Condiciones climáticas**: Impacto de viento, lluvia, altitud en el desempeño (ej. menos puntos en NFL con lluvia)
- **Lesiones y rotaciones**: Lineups de último minuto, impacto real de bajas según modelo de reemplazo
- **Fatiga y calendario**: Días de descanso entre partidos, viajes largos, congestión de fixtures

### 4.3 Capa de Análisis de Mercados (Market Intelligence)

- **Movimiento de cuotas (Odds Dropping)**: Detección de movimientos bruscos (>10% en 24h), indicador de dinero profesional
- **Comparativa de bookmakers**: Discrepancias entre casas para encontrar cuotas mal calculadas
- **Probabilidad implícita**: `implied_prob = 1 / odds` vs probabilidad calculada por el modelo
- **Detección de valor**: `edge = predicted_prob - implied_prob > threshold`

### 4.4 Capa de Sentimiento

- Escaneo de noticias recientes sobre los equipos/jugadores
- Detección de crisis internas, estados anímicos, cambios de entrenador
- Procesado por el LLM para extraer sentimiento positivo/negativo

---

## 5. Metodología de Predicción

### 5.1 Modelo Poisson
Para predecir distribución de resultados exactos (goles, puntos, sets):
```
P(x) = (λ^x × e^(-λ)) / x!
```
Donde λ se calcula a partir de las métricas ofensivas/defensivas de cada equipo.

### 5.2 Pesos del Modelo (ajustables automáticamente)

| Factor | Peso Inicial |
|--------|-------------|
| Rendimiento deportivo (stats, forma, H2H) | 40% |
| Mercado (movimiento de cuotas, valor) | 25% |
| Variables externas (clima, árbitro, lesiones) | 20% |
| Sentimiento (noticias, estado anímico) | 15% |

Los pesos se ajustan automáticamente tras cada post-mortem de apuestas fallidas.

### 5.3 Diversificación por Tipo de Deporte

| Tipo | Deportes | Enfoque Principal |
|------|----------|-------------------|
| Alta anotación | NBA, NFL | Hándicaps y totales (Over/Under) |
| Baja anotación | Fútbol, Hockey | Mercados 1X2, eventos específicos (córners, tarjetas) |
| Individuales | Tenis, UFC | Fatiga, superficie, matchup de estilos |

---

## 6. Gestión de Riesgo (Bankroll Management)

### 6.1 Criterio de Kelly
```
stake_pct = (edge × odds - 1) / (odds - 1)
```
- Capeado al 5% máximo del bankroll por apuesta
- Mínimo edge requerido: 5% para considerar la apuesta

### 6.2 Stop-Loss
- **Diario**: Si pierde >10% del bankroll en un día → se detiene
- **Semanal**: Si pierde >20% del bankroll en una semana → pausa de revisión
- **Por racha**: 3 pérdidas consecutivas → reduce stake al 50% hasta ganar

### 6.3 Bankroll Simulado
- Balance inicial: 1,000 unidades
- Cada apuesta registra stake, cuota y resultado
- Balance se actualiza automáticamente

---

## 7. Protocolo de Aprendizaje (Fase de Simulación)

### 7.1 Paper Betting
- No se realizan recomendaciones reales
- SABE selecciona eventos, aplica análisis y registra apuesta simulada
- Espera a que el evento finalice para registrar resultado (automático via API)

### 7.2 Feedback Loop (Post-Mortem)
Tras cada apuesta fallida, el LLM analiza:
- ¿Fue un factor estadístico no capturado?
- ¿Una variable externa inesperada (tarjeta roja, lesión en juego)?
- ¿Error en el cálculo de probabilidad?
- ¿El mercado tenía información que SABE no detectó?

Los pesos algorítmicos se ajustan según las conclusiones.

### 7.3 Criterio de Certificación (Go-Live)
- Se mantiene registro de win rate de las últimas 5 apuestas
- **Condición**: Solo cuando alcance ≥85% en las últimas 5 simulaciones
- SABE envía mensaje: *"Estoy preparado. He alcanzado el umbral de precisión requerido y mi modelo de análisis está optimizado"*

### 7.4 Daily Briefing (8:00 AM)
Informe automático diario que incluye:
- Resumen de la jornada anterior (apuestas, resultados, análisis de errores)
- Métrica de precisión actual (win rate últimas 5)
- Estado del modelo (qué factores se están ajustando)
- Eventos del día con potencial de valor detectado

---

## 8. Modelo de Datos (PostgreSQL)

### Tabla: `sim_bets` — Apuestas simuladas
```sql
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100)        -- usuario
sport               VARCHAR(50)         -- "football", "nba", "tennis"
event_name          VARCHAR(300)        -- "Real Madrid vs Barcelona"
event_date          TIMESTAMP           -- fecha/hora del evento
event_api_id        VARCHAR(100)        -- ID del evento en la API (para resolver)
league              VARCHAR(100)        -- "La Liga", "NBA", "ATP"
market              VARCHAR(50)         -- "1x2", "over_under", "handicap"
selection           VARCHAR(200)        -- "Real Madrid", "Over 2.5"
odds                FLOAT               -- cuota al momento
stake_pct           FLOAT               -- % del bankroll apostado
stake_units         FLOAT               -- unidades apostadas
predicted_prob      FLOAT               -- probabilidad calculada por SABE
implied_prob        FLOAT               -- probabilidad implícita de la cuota
edge                FLOAT               -- predicted_prob - implied_prob
confidence          INTEGER             -- 0-100
analysis_summary    TEXT                -- resumen del análisis completo
factors_used        JSONB               -- {"stats": 0.4, "market": 0.25, ...}
result              VARCHAR(20)         -- "pending", "win", "loss", "push", "void"
profit_loss         FLOAT               -- ganancia/pérdida en unidades
post_mortem         TEXT                -- análisis del error (si perdió)
created_at          TIMESTAMP DEFAULT NOW()
resolved_at         TIMESTAMP           -- cuándo se resolvió el evento
```

### Tabla: `sabe_model_metrics` — Evolución del modelo
```sql
id                  SERIAL PRIMARY KEY
date                DATE UNIQUE
total_bets          INTEGER
wins                INTEGER
losses              INTEGER
win_rate            FLOAT               -- % acierto general
win_rate_last_5     FLOAT               -- % últimas 5 (criterio certificación)
roi                 FLOAT               -- retorno sobre inversión
avg_edge            FLOAT               -- edge promedio
avg_confidence      FLOAT               -- confianza promedio
adjustments_made    JSONB               -- qué pesos se ajustaron
model_status        VARCHAR(20)         -- "learning", "certified", "active"
created_at          TIMESTAMP DEFAULT NOW()
```

### Tabla: `sabe_bankroll` — Estado del bankroll
```sql
id                  SERIAL PRIMARY KEY
session_id          VARCHAR(100)
initial_balance     FLOAT DEFAULT 1000  -- balance inicial simulado
current_balance     FLOAT DEFAULT 1000  -- balance actual
daily_stop_loss     FLOAT DEFAULT 0.10  -- 10% del bankroll
weekly_stop_loss    FLOAT DEFAULT 0.20  -- 20% del bankroll
max_stake_pct       FLOAT DEFAULT 0.05  -- Kelly cap 5%
min_edge            FLOAT DEFAULT 0.05  -- edge mínimo para apostar
created_at          TIMESTAMP DEFAULT NOW()
updated_at          TIMESTAMP
```

---

## 9. Actions del Agente

El agente se invoca como tool del LLM, igual que CalendarAgent o WebSearchAgent:

| Action | Descripción | Ejemplo de uso |
|--------|-------------|----------------|
| `analyze` | Análisis completo de un evento específico | "Analiza el Real Madrid vs Barcelona" |
| `scan` | Escanear eventos del día buscando value bets | "¿Qué apuestas de valor hay hoy?" |
| `bet` | Registrar apuesta simulada tras análisis | Automático tras análisis con edge suficiente |
| `history` | Últimas N apuestas simuladas con resultados | "Muéstrame el historial de SABE" |
| `metrics` | Estado del modelo (win rate, ROI, fase) | "¿Cómo va SABE?" |
| `briefing` | Generar informe de progreso | Daily automático + bajo demanda |

---

## 10. Jobs Programados

| Job | Horario | Función |
|-----|---------|---------|
| **Daily Briefing** | 8:00 AM | Genera y envía informe de progreso |
| **Result Resolver** | Cada 2 horas | Verifica resultados de eventos finalizados via API |
| **Post-Mortem** | Tras cada resolución | Analiza errores y ajusta pesos (si fue loss) |
| **Metrics Update** | 11:59 PM | Calcula métricas diarias y guarda en sabe_model_metrics |

---

## 11. Vistas

### Web: `/betting`
- **Dashboard superior**: Balance simulado, win rate últimas 5, ROI, fase del modelo
- **Tabla de apuestas**: Últimas 5+ apuestas con: evento, selección, cuota, edge, resultado, P/L
- **Post-mortem expandible**: Click en apuesta perdida para ver análisis del error
- **Indicador de fase**: Badge "Aprendizaje" (amarillo) o "Certificado" (verde)

### Mobile: `BettingScreen`
- **Card de métricas**: Win rate, balance, fase
- **Lista scrollable**: Últimas apuestas con colores (verde=win, rojo=loss, gris=pending)
- **Accesible desde Sidebar/menú**

---

## 12. Archivos a Crear/Modificar

### Nuevos archivos
| Archivo | Descripción |
|---------|-------------|
| `backend/app/models/betting.py` | Modelos SQLAlchemy (SimBet, SabeModelMetrics, SabeBankroll) |
| `backend/app/agents/betting_agent.py` | Agente SABE con todas las actions |
| `backend/app/services/sports_data_service.py` | Consumo de APIs deportivas (stats, H2H, lineups) |
| `backend/app/services/odds_service.py` | Consumo de The Odds API (cuotas, comparativas) |
| `backend/app/routers/betting.py` | Endpoints REST para las vistas web/mobile |
| `clients/web/app/betting/page.tsx` | Dashboard de betting en la web |
| `clients/sara_mobile/lib/screens/betting_screen.dart` | Pantalla de betting en la app |

### Archivos a modificar
| Archivo | Cambio |
|---------|--------|
| `backend/app/agents/__init__.py` | Registrar BettingAgent en AGENTS y AGENT_MAP |
| `backend/app/services/notification_service.py` | Agregar jobs: briefing (8am), resolver (2h), metrics (11:59pm) |
| `backend/app/services/ai_service.py` | Actualizar system prompt con instrucciones de SABE |
| `backend/app/main.py` | Importar modelo betting para auto-create tables |
| `backend/app/config.py` | Agregar API keys (ODDS_API_KEY, SPORTS_API_KEY, WEATHER_API_KEY) |
| `backend/requirements.txt` | Agregar dependencias si necesario |
| `clients/web/components/Sidebar.tsx` | Agregar link a /betting |
| `clients/sara_mobile/lib/main.dart` | Agregar ruta a BettingScreen |

---

## 13. Plan de Ejecución (Orden)

| Paso | Tarea | Dependencias |
|------|-------|-------------|
| **1** | Modelo PostgreSQL + migración | Ninguna |
| **2** | Servicios de datos: `sports_data_service.py` + `odds_service.py` | API keys configuradas |
| **3** | `BettingAgent` con actions: analyze, scan, history, metrics | Paso 1 y 2 |
| **4** | Registrar agente en `__init__.py`, actualizar system prompt | Paso 3 |
| **5** | Router REST `/betting/*` para vistas | Paso 1 |
| **6** | Jobs programados: resolver, briefing, metrics | Paso 3 |
| **7** | Vista web: `/betting` dashboard | Paso 5 |
| **8** | Vista mobile: `BettingScreen` | Paso 5 |
| **9** | Deploy: API keys en `.env.prod`, rebuild | Todo |
| **10** | Activar fase de aprendizaje y monitorear | Todo |

---

## 14. Consideraciones

### Limitaciones de APIs gratuitas
- The Odds API: 500 req/mes (~16/día) → suficiente para 3-4 análisis
- API-Football: 100 req/día → suficiente para fase de aprendizaje
- Si se necesita más volumen: planes pagos ~$20-50/mes

### Precisión realista
- El umbral de 85% es ambicioso; en betting profesional, 55-60% con buenas cuotas ya es rentable
- El modelo Poisson + value betting es el approach más fundamentado
- La fase de simulación es clave para calibrar antes de confiar
- Los pesos se irán ajustando según los resultados reales

### Impacto en el VPS
- Mínimo — solo llamadas a APIs externas y procesamiento con LLM (Groq cloud)
- Las tablas nuevas son ligeras
- Los jobs corren en horarios de baja actividad

---

*Documento generado: 2026-04-05*
*Proyecto: SARA — Agente SABE (Sistema de Análisis de Betting Estratégico)*
