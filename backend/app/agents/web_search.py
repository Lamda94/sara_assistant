from ddgs import DDGS
from .base import BaseAgent


class WebSearchAgent(BaseAgent):
    name = "web_search"
    description = (
        "Busca información actualizada en internet. "
        "Úsalo cuando el usuario pregunte sobre eventos recientes, noticias, precios, clima, "
        "personas, empresas u otra información que requiera datos actuales que no están en tu memoria."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Términos de búsqueda en el idioma más apropiado",
            },
            "max_results": {
                "type": "integer",
                "description": "Número máximo de resultados a retornar (default 4)",
            },
        },
        "required": ["query"],
    }

    async def run(self, query: str, max_results: int = 4, **_) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No se encontraron resultados para esa búsqueda."
            lines = []
            for r in results:
                lines.append(f"Título: {r['title']}\nResumen: {r['body']}\nFuente: {r['href']}")
            return "\n\n---\n\n".join(lines)
        except Exception as e:
            return f"Error al buscar en internet: {str(e)}"
