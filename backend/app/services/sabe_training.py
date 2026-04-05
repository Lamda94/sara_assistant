"""
SABE — Loop de entrenamiento autónomo.

Ciclo: genera 10 apuestas → espera resultados → analiza → ajusta pesos → repite.
Se detiene al alcanzar 85% win rate en las últimas 5.
"""
import logging
import json
import random
from datetime import datetime, date

from groq import AsyncGroq
from sqlalchemy import select, func as sqlfunc

from app.config import settings
from app.db.postgres import SessionLocal
from app.models.betting import SimBet, SabeBankroll, SabeModelMetrics

logger = logging.getLogger(__name__)
_groq = AsyncGroq(api_key=settings.groq_api_key)

# Deportes a escanear en rotación
_SPORTS = [
    "soccer_epl", "soccer_spain_la_liga", "soccer_italy_serie_a",
    "soccer_germany_bundesliga", "soccer_france_ligue_one",
    "soccer_uefa_champs_league", "basketball_nba", "americanfootball_nfl",
    "icehockey_nhl", "baseball_mlb",
]

_SESSION = "sabe-training"
_BATCH_SIZE = 10


async def sabe_training_loop():
    """
    Job principal de entrenamiento. Corre cada 3h.
    1. Verificar si ya está certificado → parar.
    2. Verificar si hay apuestas pendientes → esperar.
    3. Si todas resueltas → analizar batch, ajustar pesos.
    4. Generar nuevo batch de 10 apuestas.
    """
    logger.warning("[SABE-TRAIN] Ejecutando ciclo de entrenamiento...")

    # 1. Verificar certificación
    if await _is_certified():
        logger.warning("[SABE-TRAIN] ✅ SABE ya está certificado. Entrenamiento detenido.")
        await _notify_certified()
        return

    # 2. Verificar apuestas pendientes
    pending_count = await _count_pending()
    if pending_count > 0:
        logger.info("[SABE-TRAIN] %d apuestas pendientes. Esperando resolución.", pending_count)
        return

    # 3. Analizar batch anterior y ajustar pesos
    await _analyze_last_batch()

    # 4. Verificar certificación post-análisis
    if await _is_certified():
        logger.warning("[SABE-TRAIN] ✅ SABE alcanzó certificación tras análisis.")
        await _notify_certified()
        return

    # 5. Generar nuevo batch
    await _generate_training_batch()

    logger.warning("[SABE-TRAIN] Ciclo completado.")


async def _is_certified() -> bool:
    """Verifica si el win rate de las últimas 5 es >= 85%."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(SimBet.result)
            .where(SimBet.session_id == _SESSION)
            .where(SimBet.result.in_(["win", "loss"]))
            .order_by(SimBet.created_at.desc())
            .limit(5)
        )
        last5 = [row[0] for row in r.fetchall()]

    if len(last5) < 5:
        return False

    win_rate = sum(1 for x in last5 if x == "win") / len(last5) * 100
    return win_rate >= 85


async def _count_pending() -> int:
    """Cuenta apuestas pendientes del entrenamiento."""
    async with SessionLocal() as s:
        count = (await s.execute(
            select(sqlfunc.count(SimBet.id))
            .where(SimBet.session_id == _SESSION)
            .where(SimBet.result == "pending")
        )).scalar() or 0
    return count


async def _analyze_last_batch():
    """Analiza los resultados del último batch y ajusta pesos."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(SimBet)
            .where(SimBet.session_id == _SESSION)
            .where(SimBet.result.in_(["win", "loss"]))
            .order_by(SimBet.created_at.desc())
            .limit(_BATCH_SIZE)
        )
        bets = r.scalars().all()

    if not bets:
        logger.info("[SABE-TRAIN] No hay bets resueltas para analizar.")
        return

    wins = sum(1 for b in bets if b.result == "win")
    losses = sum(1 for b in bets if b.result == "loss")
    wr = wins / len(bets) * 100 if bets else 0

    logger.warning(
        "[SABE-TRAIN] Último batch: %d bets, %d wins, %d losses (%.0f%%)",
        len(bets), wins, losses, wr,
    )

    # Analizar patrones de error con LLM
    loss_bets = [b for b in bets if b.result == "loss"]
    if loss_bets:
        await _adjust_weights(loss_bets)


async def _adjust_weights(loss_bets: list[SimBet]):
    """Usa el LLM para analizar errores y proponer ajuste de pesos."""
    errors_summary = []
    for b in loss_bets[:5]:
        errors_summary.append(
            f"- {b.event_name} ({b.sport}): {b.market} → {b.selection} "
            f"@ {b.odds:.2f}, edge {b.edge*100:.1f}%, conf {b.confidence}%. "
            f"Post-mortem: {b.post_mortem or 'N/A'}"
        )

    resp = await _groq.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres el módulo de auto-calibración de SABE. Analiza los errores y sugiere "
                    "ajustes a los pesos del modelo. Pesos actuales: stats=0.40, market=0.25, "
                    "external=0.20, sentiment=0.15. Los pesos deben sumar 1.0.\n"
                    "Responde SOLO en JSON: {\"stats\": X, \"market\": X, \"external\": X, "
                    "\"sentiment\": X, \"reasoning\": \"...\"}"
                ),
            },
            {
                "role": "user",
                "content": f"Apuestas perdidas:\n" + "\n".join(errors_summary),
            },
        ],
        temperature=0.2,
        max_tokens=200,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        adjustment = json.loads(text)
        reasoning = adjustment.pop("reasoning", "")
        logger.warning("[SABE-TRAIN] Ajuste de pesos: %s — %s", adjustment, reasoning)

        # Guardar en métricas
        async with SessionLocal() as s:
            today = str(date.today())
            existing = (await s.execute(
                select(SabeModelMetrics).where(SabeModelMetrics.date == today)
            )).scalar_one_or_none()
            if existing:
                existing.adjustments_made = adjustment
            else:
                s.add(SabeModelMetrics(
                    date=today, adjustments_made=adjustment, model_status="learning",
                ))
            await s.commit()

    except Exception as e:
        logger.error("[SABE-TRAIN] Error parseando ajuste: %s", e)


async def _generate_training_batch():
    """Genera un batch de 10 apuestas simuladas automáticas."""
    from app.services.odds_service import get_upcoming_events, find_best_odds
    from app.services.sports_data_service import get_h2h, get_team_form

    logger.warning("[SABE-TRAIN] Generando batch de %d apuestas...", _BATCH_SIZE)

    # Recopilar eventos de múltiples deportes
    all_events = []
    sports_to_scan = random.sample(_SPORTS, min(5, len(_SPORTS)))

    for sport_key in sports_to_scan:
        try:
            events = await get_upcoming_events(sport_key)
            for ev in events:
                ev["_sport_key"] = sport_key
            all_events.extend(events)
        except Exception as e:
            logger.error("[SABE-TRAIN] Error escaneando %s: %s", sport_key, e)

    if not all_events:
        logger.warning("[SABE-TRAIN] No se encontraron eventos. Abortando batch.")
        return

    # Seleccionar eventos al azar
    random.shuffle(all_events)
    candidates = all_events[:_BATCH_SIZE * 2]  # Doble para tener de dónde filtrar

    bets_placed = 0
    for ev in candidates:
        if bets_placed >= _BATCH_SIZE:
            break

        try:
            bet_placed = await _analyze_and_bet(ev)
            if bet_placed:
                bets_placed += 1
        except Exception as e:
            logger.error("[SABE-TRAIN] Error analizando evento: %s", e)

    logger.warning("[SABE-TRAIN] Batch generado: %d/%d apuestas colocadas.", bets_placed, _BATCH_SIZE)


async def _analyze_and_bet(event: dict) -> bool:
    """Analiza un evento y coloca apuesta simulada si hay valor."""
    home = event.get("home_team", "?")
    away = event.get("away_team", "?")
    sport_key = event.get("_sport_key", "soccer")
    sport_title = event.get("sport_title", sport_key)
    event_name = f"{home} vs {away}"

    from app.services.odds_service import find_best_odds
    best = find_best_odds(event)
    if not best:
        return False

    # Obtener datos adicionales
    from app.services.sports_data_service import get_h2h, get_team_form
    h2h = []
    form_home = []
    form_away = []
    try:
        h2h = await get_h2h(home, away)
        form_home = await get_team_form(home)
        form_away = await get_team_form(away)
    except Exception:
        pass  # No bloquear si falla

    # Construir contexto
    odds_lines = [f"  {k}: {v['price']:.2f} ({v['bookmaker']})" for k, v in best.items()]
    context_parts = [
        f"Evento: {event_name}",
        f"Deporte: {sport_title}",
        f"Liga: {event.get('sport_title', 'N/A')}",
        f"Mejores cuotas:\n" + "\n".join(odds_lines),
    ]

    if h2h:
        w_home, w_away, draws = 0, 0, 0
        for f in h2h:
            gh = f.get("goals", {}).get("home", 0) or 0
            ga = f.get("goals", {}).get("away", 0) or 0
            if gh > ga:
                w_home += 1
            elif ga > gh:
                w_away += 1
            else:
                draws += 1
        context_parts.append(f"H2H: {home} {w_home}W - {draws}D - {w_away}W {away}")

    if form_home:
        results = []
        for f in form_home[:5]:
            w = f.get("teams", {}).get("home", {}).get("winner")
            results.append("W" if w is True else "L" if w is False else "D")
        context_parts.append(f"Forma {home}: {' '.join(results)}")

    if form_away:
        results = []
        for f in form_away[:5]:
            w = f.get("teams", {}).get("away", {}).get("winner")
            results.append("W" if w is True else "L" if w is False else "D")
        context_parts.append(f"Forma {away}: {' '.join(results)}")

    context = "\n".join(context_parts)

    # LLM análisis + decisión de apuesta
    resp = await _groq.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres SABE en modo ENTRENAMIENTO. Estás aprendiendo, así que DEBES apostar "
                    "en la mayoría de eventos para generar datos de aprendizaje.\n"
                    "Analiza las cuotas y los datos disponibles. Elige el resultado más probable.\n"
                    "Responde SOLO en JSON:\n"
                    '{"bet": true, "market": "h2h", '
                    '"selection": "nombre exacto del equipo/resultado de las cuotas", '
                    '"predicted_prob": 0.XX, "confidence": NN, '
                    '"analysis": "resumen breve del análisis"}\n'
                    "IMPORTANTE: selection debe coincidir EXACTAMENTE con uno de los nombres "
                    "de las cuotas proporcionadas. Apuesta siempre que tengas una opinión."
                ),
            },
            {"role": "user", "content": context},
        ],
        temperature=0.3,
        max_tokens=300,
    )

    try:
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        decision = json.loads(text)
    except Exception:
        return False

    if not decision.get("bet"):
        return False

    # Encontrar la cuota para la selección
    selection = decision.get("selection", "")
    odds = 2.0
    for name, info in best.items():
        if name.lower() in selection.lower() or selection.lower() in name.lower():
            odds = info["price"]
            break

    predicted_prob = decision.get("predicted_prob", 0.55)
    implied_prob = 1 / odds if odds > 1 else 0.5
    edge = predicted_prob - implied_prob

    if edge < 0.02:  # Threshold bajo en entrenamiento para generar más datos
        return False

    # Kelly criterion
    kelly = (edge * odds - 1) / (odds - 1) if odds > 1 else 0
    stake_pct = min(max(kelly, 0.01), 0.05)

    # Obtener/crear bankroll
    async with SessionLocal() as s:
        br = (await s.execute(
            select(SabeBankroll).where(SabeBankroll.session_id == _SESSION)
        )).scalar_one_or_none()
        if not br:
            br = SabeBankroll(session_id=_SESSION)
            s.add(br)
            await s.flush()

        stake_units = round(br.current_balance * stake_pct, 2)

        # Parsear fecha del evento (naive, sin timezone para PostgreSQL)
        event_date = datetime.utcnow()
        if event.get("commence_time"):
            try:
                dt = datetime.fromisoformat(
                    event["commence_time"].replace("Z", "+00:00")
                )
                event_date = dt.replace(tzinfo=None)
            except Exception:
                pass

        bet = SimBet(
            session_id=_SESSION,
            sport=sport_key,
            event_name=event_name,
            event_date=event_date,
            event_api_id=event.get("id"),
            league=sport_title,
            market=decision.get("market", "h2h"),
            selection=selection,
            odds=odds,
            stake_pct=stake_pct,
            stake_units=stake_units,
            predicted_prob=predicted_prob,
            implied_prob=round(implied_prob, 4),
            edge=round(edge, 4),
            confidence=decision.get("confidence", 50),
            analysis_summary=decision.get("analysis", "")[:1000],
            factors_used={"stats": 0.4, "market": 0.25, "external": 0.2, "sentiment": 0.15},
        )
        s.add(bet)
        await s.commit()

    logger.info(
        "[SABE-TRAIN] Apuesta: %s → %s @ %.2f (edge %.1f%%)",
        event_name, selection, odds, edge * 100,
    )
    return True


async def _notify_certified():
    """Envía notificación push al creador cuando SABE alcanza certificación."""
    async with SessionLocal() as s:
        # Guardar insight
        from app.models.proactive_insight import ProactiveInsight
        s.add(ProactiveInsight(
            session_id=settings.creator_id,
            type="sabe_certified",
            content=(
                "🏆 SABE CERTIFICADO — He alcanzado el umbral de precisión requerido "
                "(85%+ en las últimas 5 apuestas). Mi modelo de análisis está optimizado "
                "y estoy preparado para recomendaciones operativas."
            ),
        ))
        await s.commit()

    # Push notification
    try:
        from app.services.notification_service import _send_push
        from app.models.device_token import DeviceToken

        async with SessionLocal() as s:
            r = await s.execute(
                select(DeviceToken).where(DeviceToken.session_id.contains(settings.creator_id))
            )
            token = r.scalar_one_or_none()
            if token:
                await _send_push(
                    token.token,
                    "🏆 SABE Certificado",
                    "He alcanzado 85%+ de precisión. Estoy listo para operar.",
                )
    except Exception as e:
        logger.error("[SABE-TRAIN] Error enviando push de certificación: %s", e)
