import os
import fnmatch
from pathlib import Path
from .base import BaseAgent
from app.config import settings


class FileAgent(BaseAgent):
    name = "file_reader"
    description = (
        "Lee, lista y busca archivos en el sistema. "
        "Úsalo cuando el usuario pida leer un archivo, listar archivos de una carpeta "
        "o buscar contenido dentro de archivos."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "list", "search"],
                "description": "Acción: read=leer archivo, list=listar directorio, search=buscar texto",
            },
            "path": {
                "type": "string",
                "description": "Ruta del archivo o directorio (relativa al directorio raíz permitido)",
            },
            "query": {
                "type": "string",
                "description": "Texto a buscar dentro de los archivos (solo para action=search)",
            },
        },
        "required": ["action"],
    }

    def _allowed_root(self) -> Path | None:
        """Devuelve el directorio raíz permitido, o None si no está configurado."""
        root = settings.file_agent_root
        if not root:
            return None
        p = Path(root).expanduser().resolve()
        return p if p.exists() else None

    def _safe_path(self, root: Path, relative: str) -> Path | None:
        """Valida que la ruta resultante esté dentro del root permitido."""
        try:
            target = (root / relative).resolve()
            if not str(target).startswith(str(root)):
                return None
            return target
        except Exception:
            return None

    async def run(self, action: str, path: str = "", query: str = "", **_) -> str:
        root = self._allowed_root()
        if not root:
            return (
                "FileAgent no está configurado. "
                "Define FILE_AGENT_ROOT en el .env con el directorio que SARA puede leer."
            )

        if action == "list":
            target = self._safe_path(root, path) if path else root
            if not target or not target.exists():
                return f"El directorio '{path or root}' no existe o no está permitido."
            if not target.is_dir():
                return f"'{path}' no es un directorio."

            try:
                entries = sorted(target.iterdir(), key=lambda e: (e.is_file(), e.name))
                lines = []
                for e in entries[:50]:
                    icon = "📄" if e.is_file() else "📁"
                    size = f" ({e.stat().st_size:,} bytes)" if e.is_file() else ""
                    lines.append(f"{icon} {e.name}{size}")
                result = "\n".join(lines)
                if len(entries) > 50:
                    result += f"\n... y {len(entries) - 50} más"
                return f"Contenido de '{target.relative_to(root)}':\n{result}"
            except Exception as e:
                return f"Error listando directorio: {e}"

        elif action == "read":
            if not path:
                return "Especifica la ruta del archivo a leer."
            target = self._safe_path(root, path)
            if not target or not target.exists():
                return f"Archivo '{path}' no encontrado."
            if not target.is_file():
                return f"'{path}' no es un archivo."

            # Limitar tamaño para no saturar el contexto
            MAX_CHARS = 8000
            try:
                content = target.read_text(encoding="utf-8", errors="replace")
                truncated = len(content) > MAX_CHARS
                if truncated:
                    content = content[:MAX_CHARS]
                result = f"**{target.name}**\n```\n{content}\n```"
                if truncated:
                    result += f"\n\n*(archivo truncado — mostrando primeros {MAX_CHARS} caracteres)*"
                return result
            except Exception as e:
                return f"Error leyendo archivo: {e}"

        elif action == "search":
            if not query:
                return "Especifica el texto a buscar."

            search_root = self._safe_path(root, path) if path else root
            if not search_root or not search_root.exists():
                return f"Directorio de búsqueda '{path or root}' no encontrado."

            matches: list[str] = []
            try:
                for filepath in search_root.rglob("*"):
                    if not filepath.is_file():
                        continue
                    # Solo archivos de texto comunes
                    if filepath.suffix.lower() not in (
                        ".txt", ".md", ".py", ".js", ".ts", ".json",
                        ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh",
                        ".dart", ".tsx", ".jsx", ".html", ".css",
                    ):
                        continue
                    try:
                        text = filepath.read_text(encoding="utf-8", errors="ignore")
                        for i, line in enumerate(text.splitlines(), 1):
                            if query.lower() in line.lower():
                                rel = filepath.relative_to(root)
                                matches.append(f"{rel}:{i}  {line.strip()[:100]}")
                                if len(matches) >= 20:
                                    break
                    except Exception:
                        continue
                    if len(matches) >= 20:
                        break

                if not matches:
                    return f"No se encontró '{query}' en los archivos."
                result = "\n".join(matches)
                if len(matches) >= 20:
                    result += "\n*(mostrando primeros 20 resultados)*"
                return f"Resultados para '{query}':\n{result}"

            except Exception as e:
                return f"Error en búsqueda: {e}"

        return f"Acción '{action}' no reconocida. Usa: read, list, search."
