from slowapi import Limiter
from starlette.requests import Request


def _get_real_ip(request: Request) -> str:
    """Obtiene la IP real del cliente (nginx envía X-Real-IP)."""
    return request.headers.get("X-Real-IP", request.client.host)


limiter = Limiter(key_func=_get_real_ip)
