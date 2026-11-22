import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_timeout: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
    database_path: str = os.getenv("DATABASE_PATH", "personal_intel.db")
    auth_token: str = os.getenv("AUTH_TOKEN", "")


settings = Settings()