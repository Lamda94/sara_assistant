from .web_search import WebSearchAgent
from .reminder import ReminderAgent
from .calendar_agent import CalendarAgent
from .email_agent import EmailAgent
from .code_agent import CodeAgent
from .file_agent import FileAgent
from .betting_agent import BettingAgent

AGENTS = [
    WebSearchAgent(),
    ReminderAgent(),
    CalendarAgent(),
    EmailAgent(),
    CodeAgent(),
    FileAgent(),
    BettingAgent(),
]

# Lookup por nombre para dispatch rápido
AGENT_MAP: dict[str, object] = {a.name: a for a in AGENTS}

# Tool schemas para LLM tool calling (excluye ReminderAgent — usa keyword fast-path)
TOOL_SCHEMAS = [
    a.to_tool_schema()
    for a in AGENTS
    if a.name != "set_reminder"
]
