from app.services.llm import llm_chat, LLM_MODEL
from app.config import settings
from .base import BaseAgent


class CodeAgent(BaseAgent):
    name = "code_assistant"
    description = (
        "Genera, explica, depura y refactoriza código. "
        "Úsalo cuando el usuario pida escribir una función, script, clase, "
        "depurar un error, explicar código existente o refactorizar."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Qué debe hacer el agente (generar, explicar, depurar, refactorizar)",
            },
            "language": {
                "type": "string",
                "description": "Lenguaje de programación (python, javascript, dart, etc.)",
            },
            "code": {
                "type": "string",
                "description": "Código existente sobre el que trabajar (opcional)",
            },
        },
        "required": ["task"],
    }

    async def run(self, task: str, language: str = "python", code: str = "", **_) -> str:
        groq = llm_client

        system = (
            f"Eres un experto programador especializado en {language}. "
            "Responde de forma directa y concisa. "
            "Incluye siempre el código completo y funcional en bloques de código. "
            "Si debes explicar, sé breve y ve al punto."
        )

        user_content = task
        if code.strip():
            user_content = f"{task}\n\n```{language}\n{code.strip()}\n```"

        try:
            resp = await llm_chat("code",

                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.2,
                max_tokens=1200,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            return f"Error en CodeAgent: {e}"
