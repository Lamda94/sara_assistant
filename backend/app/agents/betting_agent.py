"""
SABE — Sistema de Análisis de Betting Estratégico.

Agente predictivo multideporte con fase de aprendizaje por simulación.
Actions: analyze, scan, bet, history, metrics, briefing
"""
import logging
import math
from datetime import datetime, date

from app.services.llm import llm_chat, LLM_MODEL
from app.config import settings
from .base import BaseAgent

logger = logging.getLogger(__name__)
# llm_client importado desde app.services.llm


class BettingAgent(BaseAgent):
    name = "betting"
    description = (
        "Agente SABE — analista predictivo de apuestas deportivas. "
        "Analiza eventos deportivos, detecta value bets, gestiona apuestas simuladas "
        "y genera informes de rendimiento. Usa múltiples capas de datos: "
        "estadísticas, cuotas, clima, lesiones y sentimiento."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["analyze", "scan", "history", "metrics", "briefing"],
                "description": (
                    "analyze: análisis completo de un evento. "
                    "scan: escanear value bets del día. "
                    "history: últimas apuestas simuladas. "
                    "metrics: estado del modelo. "
                    "briefing: informe de progreso."
                ),
            },
            "sport": {
                "type": "string",
                "description": "Deporte: soccer, nba, nfl, tennis, ufc, etc.",
            },
            "event": {
                "type": "string",
                "description": "Nombre del evento o equipos (ej: 'Real Madrid vs Barcelona')",
            },
            "limit": {
                "type": "integer",
                "description": "Cantidad de resultados a mostrar (default 5)",
            },
        },
        "required": ["action"],
    }

    async def run(self, action: str, sport: str = "soccer", event: str = "",
                  limit: int = 5, session_id: str = "", **_) -> str:
        try:
            if action == "analyze":
                return await self._analyze(sport, event, session_id)
            elif action == "scan":
                return await self._scan(sport, limit, session_id)
            elif action == "history":
                return await self._history(session_id, limit)
            elif action == "metrics":
                return await self._metrics(session_id)
            elif action == "briefing":
                return await self._briefing(session_id)
            else:
                return f"Acción desconocida: {action}"
        except Exception as e:
            logger.error(f"SABE error ({action}): {e}")
            return f"Error en SABE: {str(e)}"

    # ─── ANALYZE ─────────────────────────────────────────────

    async def _analyze(self, sport: str, event: str, session_id: str) -> str:
        if not event:
            return "Necesito el nombre del evento o los equipos para analizar."

        from app.services.odds_service import get_upcoming_events, find_best_odds
        from app.services.sports_data_service import get_h2h, get_team_form, get_weather

        # 1. Buscar el evento en las cuotas
        events = await get_upcoming_events(sport)
        target = self._find_event(events, event)

        # 2. Recopilar datos
        teams = event.split(" vs ") if " vs " in event else event.split(" - ")
        team1 = teams[0].strip() if len(teams) >= 1 else event
        team2 = teams[1].strip() if len(teams) >= 2 else ""

        h2h = await get_h2h(team1, team2) if team2 else []
        form1 = await get_team_form(team1)
        form2 = await get_team_form(team2) if team2 else []

        # 3. Obtener mejores cuotas
        odds_info = ""
        if target:
            best = find_best_odds(target)
            odds_lines = [f"  {k}: {v['price']:.2f} ({v['bookmaker']})" for k, v in best.items()]
            odds_info = "Mejores cuotas:\n" + "\n".join(odds_lines)

        # 4. Construir contexto para el LLM
        context_parts = [f"Evento: {event}", f"Deporte: {sport}"]

        if odds_info:
            context_parts.append(odds_info)

        if h2h:
            h2h_summary = self._summarize_h2h(h2h, team1, team2)
            context_parts.append(f"H2H últimos {len(h2h)} partidos:\n{h2h_summary}")

        if form1:
            context_parts.append(f"Forma {team1} (últimos {len(form1)}):\n{self._summarize_form(form1)}")
        if form2:
            context_parts.append(f"Forma {team2} (últimos {len(form2)}):\n{self._summarize_form(form2)}")

        context = "\n\n".join(context_parts)

        # 5. Análisis con LLM
        analysis = await self._llm_analyze(context, sport)

        # 6. Registrar apuesta simulada si hay edge
        bet_info = await self._maybe_place_bet(analysis, target, sport, event, session_id)

        return f"{analysis}\n\n{bet_info}" if bet_info else analysis

    # ─── SCAN ────────────────────────────────────────────────

    async def _scan(self, sport: str, limit: int, session_id: str) -> str:
        from app.services.odds_service import get_upcoming_events, find_best_odds

        events = await get_upcoming_events(sport)
        if not events:
            return f"No se encontraron eventos próximos para {sport}."

        results = []
        for ev in events[:limit]:
            home = ev.get("home_team", "?")
            away = ev.get("away_team", "?")
            best = find_best_odds(ev)

            if best:
                odds_str = " | ".join(f"{k}: {v['price']:.2f}" for k, v in best.items())
                results.append(f"⚽ {home} vs {away}\n  Cuotas: {odds_str}")

        if not results:
            return "No se encontraron eventos con cuotas disponibles."

        header = f"📊 **Eventos próximos — {sport.upper()}** ({len(results)} encontrados)\n"
        return header + "\n\n".join(results)

    # ─── HISTORY ─────────────────────────────────────────────

    async def _history(self, session_id: str, limit: int) -> str:
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.betting import SimBet

        async with SessionLocal() as s:
            r = await s.execute(
                select(SimBet)
                .order_by(SimBet.created_at.desc())
                .limit(limit)
            )
            bets = r.scalars().all()

        if not bets:
            return "No hay apuestas simuladas registradas aún."

        lines = ["📋 **Historial de apuestas simuladas**\n"]
        for i, b in enumerate(bets, 1):
            icon = "✅" if b.result == "win" else "❌" if b.result == "loss" else "⏳"
            pl = f"+{b.profit_loss:.1f}" if b.profit_loss > 0 else f"{b.profit_loss:.1f}"
            lines.append(
                f"{i}. {icon} **{b.event_name}**\n"
                f"   {b.market} → {b.selection} @ {b.odds:.2f}\n"
                f"   Edge: {b.edge*100:.1f}% | Confianza: {b.confidence}%\n"
                f"   Resultado: {b.result.upper()} ({pl}u)"
            )

        # Win rate últimas 5
        resolved = [b for b in bets if b.result in ("win", "loss")]
        last5 = resolved[:5]
        if last5:
            wr = sum(1 for b in last5 if b.result == "win") / len(last5) * 100
            lines.append(f"\n📈 Win rate últimas {len(last5)}: **{wr:.0f}%**")

        return "\n\n".join(lines)

    # ─── METRICS ─────────────────────────────────────────────

    async def _metrics(self, session_id: str) -> str:
        from sqlalchemy import select, func as sqlfunc
        from app.db.postgres import SessionLocal
        from app.models.betting import SimBet, SabeBankroll

        async with SessionLocal() as s:
            # Total bets
            total = (await s.execute(select(sqlfunc.count(SimBet.id)))).scalar() or 0
            wins = (await s.execute(
                select(sqlfunc.count(SimBet.id)).where(SimBet.result == "win")
            )).scalar() or 0
            losses = (await s.execute(
                select(sqlfunc.count(SimBet.id)).where(SimBet.result == "loss")
            )).scalar() or 0
            pending = (await s.execute(
                select(sqlfunc.count(SimBet.id)).where(SimBet.result == "pending")
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

            # Bankroll
            br = (await s.execute(select(SabeBankroll).limit(1))).scalar_one_or_none()
            balance = br.current_balance if br else 1000.0

            # ROI
            total_profit = (await s.execute(
                select(sqlfunc.sum(SimBet.profit_loss)).where(SimBet.result.in_(["win", "loss"]))
            )).scalar() or 0
            roi = (total_profit / 1000.0) * 100

        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        status = "certified" if wr5 >= 85 and len(last5) >= 5 else "learning"

        return (
            f"📊 **Estado SABE**\n\n"
            f"Fase: **{'✅ Certificado' if status == 'certified' else '🔄 Aprendizaje'}**\n"
            f"Total apuestas: {total} ({pending} pendientes)\n"
            f"Ganadas: {wins} | Perdidas: {losses}\n"
            f"Win rate general: {win_rate:.1f}%\n"
            f"Win rate últimas 5: **{wr5:.0f}%** {'✅' if wr5 >= 85 else ''}\n"
            f"ROI: {roi:+.1f}%\n"
            f"Balance: {balance:.0f} unidades"
        )

    # ─── BRIEFING ────────────────────────────────────────────

    async def _briefing(self, session_id: str) -> str:
        metrics = await self._metrics(session_id)
        history = await self._history(session_id, 5)
        return f"🌅 **Informe SABE — {date.today().strftime('%d/%m/%Y')}**\n\n{metrics}\n\n---\n\n{history}"

    # ─── Helpers privados ────────────────────────────────────

    def _find_event(self, events: list, query: str) -> dict | None:
        """Busca un evento que coincida con la query."""
        q = query.lower()
        for ev in events:
            home = ev.get("home_team", "").lower()
            away = ev.get("away_team", "").lower()
            if any(t in q for t in [home, away]) or any(t in home or t in away for t in q.split()):
                return ev
        return None

    def _summarize_h2h(self, fixtures: list, team1: str, team2: str) -> str:
        lines = []
        t1_lower = team1.lower()
        w1, w2, draws = 0, 0, 0
        for f in fixtures:
            home = f.get("teams", {}).get("home", {})
            away = f.get("teams", {}).get("away", {})
            gh = f.get("goals", {}).get("home", 0) or 0
            ga = f.get("goals", {}).get("away", 0) or 0
            if gh > ga:
                if home.get("name", "").lower().startswith(t1_lower[:4]):
                    w1 += 1
                else:
                    w2 += 1
            elif ga > gh:
                if away.get("name", "").lower().startswith(t1_lower[:4]):
                    w1 += 1
                else:
                    w2 += 1
            else:
                draws += 1
        return f"  {team1}: {w1}W | {team2}: {w2}W | Empates: {draws}"

    def _summarize_form(self, fixtures: list) -> str:
        form = []
        for f in fixtures:
            home = f.get("teams", {}).get("home", {})
            away = f.get("teams", {}).get("away", {})
            gh = f.get("goals", {}).get("home", 0) or 0
            ga = f.get("goals", {}).get("away", 0) or 0
            winner = home.get("winner")
            result = "W" if winner is True else "L" if winner is False else "D"
            form.append(f"  {home.get('name', '?')} {gh}-{ga} {away.get('name', '?')} ({result})")
        return "\n".join(form) if form else "  Sin datos"

    async def _llm_analyze(self, context: str, sport: str) -> str:
        """Usa el LLM para generar el análisis predictivo."""
        resp = await llm_chat("reasoning",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres SABE, un analista predictivo de apuestas deportivas experto. "
                        "Analiza los datos proporcionados y genera:\n"
                        "1. Resumen de la situación de cada equipo/jugador\n"
                        "2. Factores clave que influyen en el resultado\n"
                        "3. Probabilidades calculadas para cada resultado\n"
                        "4. Value bet recomendado (si existe edge > 5%)\n"
                        "5. Nivel de confianza (0-100)\n"
                        "6. Mercado recomendado (1X2, Over/Under, Handicap)\n\n"
                        "Sé directo y analítico. Usa datos, no intuición. "
                        "Si no hay suficientes datos, indícalo claramente."
                    ),
                },
                {"role": "user", "content": context},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()

    async def _maybe_place_bet(self, analysis: str, event_data: dict | None,
                                sport: str, event_name: str, session_id: str) -> str:
        """Intenta extraer una apuesta del análisis y registrarla como simulada."""
        # Extraer datos de la apuesta usando LLM
        resp = await llm_chat("reasoning",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "Del análisis de apuestas, extrae en formato JSON:\n"
                        '{"place_bet": true/false, "market": "1x2/over_under/handicap", '
                        '"selection": "nombre", "predicted_prob": 0.XX, "confidence": NN, '
                        '"odds": X.XX}\n'
                        "Si no hay value bet claro, pon place_bet: false. "
                        "Solo responde con el JSON, nada más."
                    ),
                },
                {"role": "user", "content": analysis},
            ],
            temperature=0.1,
            max_tokens=150,
        )

        import json
        try:
            text = resp.choices[0].message.content.strip()
            # Limpiar markdown si viene envuelto
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            bet_data = json.loads(text)
        except Exception:
            return ""

        if not bet_data.get("place_bet"):
            return "📝 No se detectó value bet suficiente para registrar apuesta simulada."

        odds = bet_data.get("odds", 2.0)
        predicted_prob = bet_data.get("predicted_prob", 0.5)
        implied_prob = 1 / odds if odds > 1 else 0.5
        edge = predicted_prob - implied_prob
        confidence = bet_data.get("confidence", 50)

        if edge < 0.05:
            return "📝 Edge insuficiente (<5%). No se registra apuesta."

        # Calcular stake con Kelly
        kelly = (edge * odds - 1) / (odds - 1) if odds > 1 else 0
        stake_pct = min(kelly, 0.05)  # Cap 5%
        stake_pct = max(stake_pct, 0.01)  # Min 1%

        # Obtener o crear bankroll
        from sqlalchemy import select
        from app.db.postgres import SessionLocal
        from app.models.betting import SimBet, SabeBankroll

        async with SessionLocal() as s:
            br = (await s.execute(
                select(SabeBankroll).where(SabeBankroll.session_id == (session_id or "default"))
            )).scalar_one_or_none()
            if not br:
                br = SabeBankroll(session_id=session_id or "default")
                s.add(br)
                await s.flush()

            stake_units = br.current_balance * stake_pct

            # Crear apuesta simulada
            bet = SimBet(
                session_id=session_id or "default",
                sport=sport,
                event_name=event_name,
                event_date=datetime.fromisoformat(event_data["commence_time"].replace("Z", "+00:00")) if event_data and "commence_time" in event_data else datetime.utcnow(),
                event_api_id=event_data.get("id") if event_data else None,
                league=event_data.get("sport_title") if event_data else None,
                market=bet_data.get("market", "1x2"),
                selection=bet_data.get("selection", "?"),
                odds=odds,
                stake_pct=stake_pct,
                stake_units=round(stake_units, 2),
                predicted_prob=predicted_prob,
                implied_prob=round(implied_prob, 4),
                edge=round(edge, 4),
                confidence=confidence,
                analysis_summary=analysis[:1000],
                factors_used={"stats": 0.4, "market": 0.25, "external": 0.2, "sentiment": 0.15},
            )
            s.add(bet)
            await s.commit()

        return (
            f"🎯 **Apuesta simulada registrada**\n"
            f"  Mercado: {bet_data.get('market')} → {bet_data.get('selection')}\n"
            f"  Cuota: {odds:.2f} | Edge: {edge*100:.1f}%\n"
            f"  Confianza: {confidence}% | Stake: {stake_units:.1f}u ({stake_pct*100:.1f}%)\n"
            f"  Estado: ⏳ PENDIENTE"
        )
