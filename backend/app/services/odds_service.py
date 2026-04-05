"""Servicio de cuotas — The Odds API."""
import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

_BASE = "https://api.the-odds-api.com/v4"


async def get_upcoming_events(sport: str = "soccer", regions: str = "eu,us", markets: str = "h2h") -> list[dict]:
    """Obtiene eventos próximos con cuotas de múltiples bookmakers."""
    sport_key = _map_sport(sport)
    url = f"{_BASE}/sports/{sport_key}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error(f"Odds API error: {e}")
        return []


async def get_event_odds(sport: str, event_id: str, markets: str = "h2h,totals,spreads") -> dict | None:
    """Obtiene cuotas detalladas de un evento específico."""
    sport_key = _map_sport(sport)
    url = f"{_BASE}/sports/{sport_key}/events/{event_id}/odds"
    params = {
        "apiKey": settings.odds_api_key,
        "regions": "eu,us",
        "markets": markets,
        "oddsFormat": "decimal",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error(f"Odds API event error: {e}")
        return None


async def get_sports() -> list[dict]:
    """Lista todos los deportes disponibles."""
    url = f"{_BASE}/sports"
    params = {"apiKey": settings.odds_api_key}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            return [s for s in r.json() if not s.get("has_outrights")]
    except Exception as e:
        logger.error(f"Odds API sports error: {e}")
        return []


def find_best_odds(event: dict, market: str = "h2h") -> dict:
    """Encuentra las mejores cuotas entre bookmakers para cada outcome."""
    best = {}
    for bm in event.get("bookmakers", []):
        for mkt in bm.get("markets", []):
            if mkt["key"] != market:
                continue
            for outcome in mkt["outcomes"]:
                name = outcome["name"]
                price = outcome["price"]
                if name not in best or price > best[name]["price"]:
                    best[name] = {"price": price, "bookmaker": bm["title"]}
    return best


def _map_sport(sport: str) -> str:
    """Mapea nombre común a sport_key de The Odds API."""
    mapping = {
        "soccer": "soccer_epl",
        "football": "soccer_epl",
        "futbol": "soccer_epl",
        "premier": "soccer_epl",
        "laliga": "soccer_spain_la_liga",
        "la liga": "soccer_spain_la_liga",
        "liga española": "soccer_spain_la_liga",
        "serie a": "soccer_italy_serie_a",
        "bundesliga": "soccer_germany_bundesliga",
        "ligue 1": "soccer_france_ligue_one",
        "champions": "soccer_uefa_champs_league",
        "nba": "basketball_nba",
        "nfl": "americanfootball_nfl",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
        "tennis": "tennis_atp_french_open",
        "ufc": "mma_mixed_martial_arts",
        "mma": "mma_mixed_martial_arts",
    }
    return mapping.get(sport.lower(), sport)
