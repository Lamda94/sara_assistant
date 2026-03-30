from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"

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

    class Config:
        env_file = ".env"


settings = Settings()
