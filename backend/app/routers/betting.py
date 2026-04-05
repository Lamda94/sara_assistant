"""BettingRouter — Endpoints REST para las vistas de SABE."""
from fastapi import APIRouter, Request
from sqlalchemy import select, func as sqlfunc
from app.db.postgres import SessionLocal
from app.models.betting import SimBet, SabeModelMetrics, SabeBankroll
from app.limiter import limiter

router = APIRouter(prefix="/betting", tags=["betting"])


@router.get("/history")
@limiter.limit("30/minute")
async def get_history(request: Request, limit: int = 10):
    """Últimas N apuestas simuladas."""
    async with SessionLocal() as s:
        r = await s.execute(
            select(SimBet).order_by(SimBet.created_at.desc()).limit(limit)
        )
        bets = r.scalars().all()

    return [
        {
            "id": b.id,
            "sport": b.sport,
            "event_name": b.event_name,
            "event_date": b.event_date.isoformat() if b.event_date else None,
            "league": b.league,
            "market": b.market,
            "selection": b.selection,
            "odds": b.odds,
            "stake_units": b.stake_units,
            "predicted_prob": b.predicted_prob,
            "implied_prob": b.implied_prob,
            "edge": b.edge,
            "confidence": b.confidence,
            "analysis_summary": b.analysis_summary,
            "result": b.result,
            "profit_loss": b.profit_loss,
            "post_mortem": b.post_mortem,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "resolved_at": b.resolved_at.isoformat() if b.resolved_at else None,
        }
        for b in bets
    ]


@router.get("/metrics")
@limiter.limit("30/minute")
async def get_metrics(request: Request):
    """Métricas generales del modelo SABE."""
    async with SessionLocal() as s:
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

        # ROI y profit total
        total_profit = (await s.execute(
            select(sqlfunc.sum(SimBet.profit_loss)).where(SimBet.result.in_(["win", "loss"]))
        )).scalar() or 0
        roi = (total_profit / 1000.0) * 100

        # Avg edge y confidence
        avg_edge = (await s.execute(
            select(sqlfunc.avg(SimBet.edge)).where(SimBet.result.in_(["win", "loss"]))
        )).scalar() or 0
        avg_conf = (await s.execute(
            select(sqlfunc.avg(SimBet.confidence)).where(SimBet.result.in_(["win", "loss"]))
        )).scalar() or 0

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    status = "certified" if wr5 >= 85 and len(last5) >= 5 else "learning"

    return {
        "model_status": status,
        "total_bets": total,
        "wins": wins,
        "losses": losses,
        "pending": pending,
        "win_rate": round(win_rate, 1),
        "win_rate_last_5": round(wr5, 1),
        "roi": round(roi, 1),
        "balance": round(balance, 1),
        "total_profit": round(total_profit, 1),
        "avg_edge": round(avg_edge * 100, 1) if avg_edge else 0,
        "avg_confidence": round(avg_conf, 1) if avg_conf else 0,
    }
