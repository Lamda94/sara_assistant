"""Servicio de datos deportivos — API-Football + OpenWeather."""
import logging
from datetime import date
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

_FOOTBALL_BASE = "https://v3.football.api-sports.io"
_WEATHER_BASE = "https://api.openweathermap.org/data/2.5"


# ─── FÚTBOL ─────────────────────────────────────────────────

async def get_team_stats(team_name: str, league_id: int = None, season: int = None) -> dict | None:
    """Estadísticas de un equipo (forma, goles, etc.)."""
    season = season or date.today().year
    team_id = await _search_team(team_name)
    if not team_id:
        return None
    if not league_id:
        league_id = await _get_team_league(team_id, season)
    if not league_id:
        return None

    data = await _football_get("teams/statistics", {
        "team": team_id, "league": league_id, "season": season,
    })
    return data.get("response") if data else None


async def get_h2h(team1: str, team2: str, last: int = 10) -> list[dict]:
    """Head-to-head entre dos equipos."""
    id1 = await _search_team(team1)
    id2 = await _search_team(team2)
    if not id1 or not id2:
        return []
    data = await _football_get("fixtures/headtohead", {
        "h2h": f"{id1}-{id2}", "last": last,
    })
    return data.get("response", []) if data else []


async def get_fixtures_today(league_id: int = None) -> list[dict]:
    """Partidos del día (opcionalmente filtrado por liga)."""
    params = {"date": str(date.today())}
    if league_id:
        params["league"] = league_id
    data = await _football_get("fixtures", params)
    return data.get("response", []) if data else []


async def get_fixture_lineups(fixture_id: int) -> list[dict]:
    """Alineaciones de un partido."""
    data = await _football_get("fixtures/lineups", {"fixture": fixture_id})
    return data.get("response", []) if data else []


async def get_fixture_predictions(fixture_id: int) -> dict | None:
    """Predicciones de API-Football para un partido."""
    data = await _football_get("predictions", {"fixture": fixture_id})
    resp = data.get("response", []) if data else []
    return resp[0] if resp else None


async def get_injuries(team_id: int = None, fixture_id: int = None) -> list[dict]:
    """Lesiones actuales de un equipo o partido."""
    params = {}
    if fixture_id:
        params["fixture"] = fixture_id
    elif team_id:
        params["team"] = team_id
    if not params:
        return []
    data = await _football_get("injuries", params)
    return data.get("response", []) if data else []


async def get_team_form(team_name: str, last: int = 5) -> list[dict]:
    """Últimos N partidos de un equipo con resultados."""
    team_id = await _search_team(team_name)
    if not team_id:
        return []
    data = await _football_get("fixtures", {
        "team": team_id, "last": last, "status": "FT",
    })
    return data.get("response", []) if data else []


# ─── CLIMA ───────────────────────────────────────────────────

async def get_weather(city: str) -> dict | None:
    """Obtiene clima actual de una ciudad."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{_WEATHER_BASE}/weather", params={
                "q": city, "appid": settings.weather_api_key,
                "units": "metric", "lang": "es",
            })
            r.raise_for_status()
            data = r.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"],
                "description": data["weather"][0]["description"],
                "rain": data.get("rain", {}).get("1h", 0),
            }
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return None


# ─── Helpers internos ────────────────────────────────────────

async def _football_get(endpoint: str, params: dict) -> dict | None:
    """Request genérico a API-Football."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{_FOOTBALL_BASE}/{endpoint}",
                params=params,
                headers={"x-apisports-key": settings.sports_api_key},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.error(f"API-Football error ({endpoint}): {e}")
        return None


async def _search_team(name: str) -> int | None:
    """Busca un equipo por nombre y retorna su ID."""
    data = await _football_get("teams", {"search": name})
    teams = data.get("response", []) if data else []
    if teams:
        return teams[0]["team"]["id"]
    return None


async def _get_team_league(team_id: int, season: int) -> int | None:
    """Obtiene la liga principal de un equipo."""
    data = await _football_get("leagues", {"team": team_id, "season": season})
    leagues = data.get("response", []) if data else []
    if leagues:
        return leagues[0]["league"]["id"]
    return None
