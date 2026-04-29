"""
Servicio SABE — Jobs programados para resolver apuestas y generar briefings.
"""
import logging
from datetime import datetime, date

from app.services.llm import llm_chat, LLM_MODEL
from sqlalchemy import select
from app.config import settings
from app.db.postgres import SessionLocal
from app.models.betting import SimBet, SabeBankroll, SabeModelMetrics

logger = logging.getLogger(__name__)
# llm_client importado desde app.services.llm


async def resolve_pending_bets():
    """
    Job que corre cada 3h: busca apuestas pendientes cuyo evento ya pasó
    y resuelve el resultado consultando la API de scores.
    """
    from app.services.odds_service import _map_sport

    logger.info("[SABE] Resolviendo apuestas pendientes...")

    async with SessionLocal() as s:
        r = await s.execute(
            select(SimBet).where(
                SimBet.result == "pending",
                SimBet.event_date < datetime.utcnow(),
            )
        )
        pending = r.scalars().all()

        if not pending:
            logger.info("[SABE] No hay apuestas pendientes por resolver")
            return

        for bet in pending:
            try:
                result = await _resolve_single_bet(bet)
                if result is None:
                    continue  # Evento aún no tiene resultado

                bet.result = result
                bet.resolved_at = datetime.utcnow()

                if result == "win":
                    bet.profit_loss = round(bet.stake_units * (bet.odds - 1), 2)
                elif result == "loss":
                    bet.profit_loss = -bet.stake_units

                # Actualizar bankroll
                br = (await s.execute(
                    select(SabeBankroll).where(SabeBankroll.session_id == bet.session_id)
                )).scalar_one_or_none()
                if br:
                    br.current_balance = round(br.current_balance + bet.profit_loss, 2)

                # Post-mortem si perdió
                if result == "loss":
                    bet.post_mortem = await _generate_post_mortem(bet)

                logger.warning(
                    "[SABE] Resuelto: %s → %s (P/L: %+.1f)",
                    bet.event_name, result, bet.profit_loss,
                )

            except Exception as e:
                logger.error("[SABE] Error resolviendo %s: %s", bet.id, e)

        await s.commit()

    # Actualizar métricas diarias
    await _update_daily_metrics()
    logger.info("[SABE] Resolución completada")


async def _resolve_single_bet(bet: SimBet) -> str | None:
    """
    Intenta resolver una apuesta individual consultando scores.
    Retorna 'win', 'loss', 'push' o None si no hay resultado aún.
    """
    import httpx

    if not bet.event_api_id:
        # Sin API ID, intentar resolver por tiempo (si pasaron >3h del evento)
        hours_since = (datetime.utcnow() - bet.event_date).total_seconds() / 3600
        if hours_since < 3:
            return None
        # Usar LLM para buscar el resultado
        return await _resolve_via_search(bet)

    # Intentar con The Odds API scores
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://api.the-odds-api.com/v4/sports/{bet.sport}/scores",
                params={
                    "apiKey": settings.odds_api_key,
                    "daysFrom": 3,
                },
            )
            r.raise_for_status()
            scores = r.json()

        for game in scores:
            if game.get("id") == bet.event_api_id and game.get("completed"):
                return _check_bet_result(bet, game)

    except Exception as e:
        logger.error("[SABE] Scores API error: %s", e)

    return None


async def _resolve_via_search(bet: SimBet) -> str | None:
    """Usa búsqueda web + LLM para resolver una apuesta sin API ID."""
    from app.agents.web_search import WebSearchAgent

    searcher = WebSearchAgent()
    query = f"resultado {bet.event_name} {bet.event_date.strftime('%d/%m/%Y')}"
    search_result = await searcher.run(query=query, max_results=3)

    resp = await llm_chat("reasoning",

        messages=[
            {
                "role": "system",
                "content": (
                    "Determina el resultado de esta apuesta deportiva basándote en los resultados de búsqueda. "
                    "Responde SOLO con: win, loss, push, o unknown (si no puedes determinar el resultado)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Apuesta: {bet.event_name}\n"
                    f"Mercado: {bet.market}\n"
                    f"Selección: {bet.selection}\n"
                    f"Resultados de búsqueda:\n{search_result}"
                ),
            },
        ],
        temperature=0.1,
        max_tokens=20,
    )
    result = resp.choices[0].message.content.strip().lower()
    return result if result in ("win", "loss", "push") else None


def _check_bet_result(bet: SimBet, game: dict) -> str:
    """Verifica si la apuesta ganó o perdió basándose en scores."""
    scores = game.get("scores", [])
    if not scores or len(scores) < 2:
        return "void"

    home_score = int(scores[0].get("score", 0))
    away_score = int(scores[1].get("score", 0))
    home_team = game.get("home_team", "")
    away_team = game.get("away_team", "")
    selection = bet.selection.lower()

    if bet.market in ("1x2", "h2h"):
        if home_score > away_score and home_team.lower() in selection:
            return "win"
        elif away_score > home_score and away_team.lower() in selection:
            return "win"
        elif home_score == away_score and "draw" in selection:
            return "win"
        return "loss"

    elif bet.market == "over_under":
        total = home_score + away_score
        if "over" in selection:
            try:
                line = float(selection.split()[-1])
                return "win" if total > line else "loss"
            except ValueError:
                pass
        elif "under" in selection:
            try:
                line = float(selection.split()[-1])
                return "win" if total < line else "loss"
            except ValueError:
                pass

    return "loss"  # Default


async def _generate_post_mortem(bet: SimBet) -> str:
    """Genera análisis post-mortem de una apuesta perdida."""
    resp = await llm_chat("reasoning",

        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un analista de apuestas. Analiza por qué esta apuesta perdió. "
                    "Considera: ¿fue un factor estadístico no capturado? ¿Variable externa inesperada? "
                    "¿Error en el cálculo de probabilidad? ¿El mercado tenía información que no detectamos? "
                    "Sé conciso (máximo 3 oraciones). Sugiere un ajuste específico."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Evento: {bet.event_name}\n"
                    f"Mercado: {bet.market} → {bet.selection}\n"
                    f"Cuota: {bet.odds} | Prob predicha: {bet.predicted_prob*100:.0f}%\n"
                    f"Edge: {bet.edge*100:.1f}% | Confianza: {bet.confidence}%\n"
                    f"Análisis original:\n{bet.analysis_summary[:500]}"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return resp.choices[0].message.content.strip()


async def _update_daily_metrics():
    """Actualiza las métricas diarias del modelo."""
    today = str(date.today())

    async with SessionLocal() as s:
        from sqlalchemy import func as sqlfunc

        total = (await s.execute(select(sqlfunc.count(SimBet.id)))).scalar() or 0
        wins = (await s.execute(
            select(sqlfunc.count(SimBet.id)).where(SimBet.result == "win")
        )).scalar() or 0
        losses = (await s.execute(
            select(sqlfunc.count(SimBet.id)).where(SimBet.result == "loss")
        )).scalar() or 0

        # Win rate últimas 5
        r = await s.execute(
            select(SimBet.result)
            .where(SimBet.result.in_(["win", "loss"]))
            .order_by(SimBet.created_at.desc())
            .limit(5)
        )
        last5 = [row[0] for row in r.fetchall()]
        wr5 = sum(1 for x in last5 if x == "win") / len(last5) * 100 if last5 else 0

        total_profit = (await s.execute(
            select(sqlfunc.sum(SimBet.profit_loss)).where(SimBet.result.in_(["win", "loss"]))
        )).scalar() or 0
        roi = (total_profit / 1000.0) * 100

        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        status = "certified" if wr5 >= 85 and len(last5) >= 5 else "learning"

        # Upsert métricas del día
        existing = (await s.execute(
            select(SabeModelMetrics).where(SabeModelMetrics.date == today)
        )).scalar_one_or_none()

        if existing:
            existing.total_bets = total
            existing.wins = wins
            existing.losses = losses
            existing.win_rate = round(win_rate, 1)
            existing.win_rate_last_5 = round(wr5, 1)
            existing.roi = round(roi, 1)
            existing.model_status = status
        else:
            s.add(SabeModelMetrics(
                date=today,
                total_bets=total,
                wins=wins,
                losses=losses,
                win_rate=round(win_rate, 1),
                win_rate_last_5=round(wr5, 1),
                roi=round(roi, 1),
                model_status=status,
            ))

        await s.commit()


async def sabe_daily_briefing():
    """Job de las 8am — genera briefing y envía como push notification."""
    logger.warning("[SABE] Generando daily briefing...")

    from app.agents.betting_agent import BettingAgent
    agent = BettingAgent()
    briefing = await agent._briefing("default")

    # Guardar como insight proactivo
    from app.models.proactive_insight import ProactiveInsight
    async with SessionLocal() as s:
        s.add(ProactiveInsight(
            session_id=settings.creator_id,
            type="sabe_briefing",
            content=briefing[:2000],
        ))
        await s.commit()

    logger.warning("[SABE] Daily briefing guardado como insight")
