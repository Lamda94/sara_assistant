from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    ollama_host: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"

    database_url: str
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "sara_memories"

    app_name: str = "SARA"
    memory_top_k: int = 5
    public_url: str = "http://localhost:8000"
    firebase_credentials_path: str = ""
    mem0_api_key: str = ""            # vacío = modo local, definido = Mem0 cloud
    google_credentials_path: str = "" # para CalendarAgent y EmailAgent
    file_agent_root: str = ""         # directorio raíz que FileAgent puede leer

    # --- Proactivity (Phase 5.2) ---
    proactive_check_interval_hours: int = 2
    proactive_start_hour: int = 8        # No molestar antes de las 8am
    proactive_end_hour: int = 22         # No molestar después de las 10pm
    proactive_inactivity_hours: int = 48  # Alertar si no hay interacción en 48h
    proactive_max_daily_pushes: int = 3   # Máximo pushes proactivos por día por usuario

    # --- Security (Phase 5.5) ---
    creator_email: str = "lamda94@gmail.com"
    creator_id: str = "lamda94"
    sara_api_key: str = ""          # vacío = sin verificación (dev)
    allowed_origins: str = ""       # comma-separated; vacío = "*" (dev)

    # --- SABE Agent (Betting) ---
    odds_api_key: str = ""
    sports_api_key: str = ""
    weather_api_key: str = ""

    # --- Consolidation (Phase 4.2) ---
    consolidation_similarity_threshold: float = 0.88
    consolidation_max_points_per_user: int = 500
    consolidation_old_facts_days: int = 60
    consolidation_min_facts_for_summary: int = 2
    consolidation_importance_decay_days: int = 30
    consolidation_cron_hour: int = 3
    consolidation_cron_minute: int = 0

    class Config:
        env_file = ".env"


settings = Settings()
