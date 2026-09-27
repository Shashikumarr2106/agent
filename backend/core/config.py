import os
import json
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def load_dotenv():
    """Lightweight .env loader without requiring external python-dotenv."""
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key not in os.environ:
                    os.environ[key] = val

load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

    # Database: fallback to sqlite if postgres is not configured
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent.db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "agent_db")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Embedding Settings
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "deterministic")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    # MCP Settings
    MCP_SERVER_HOST: str = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    MCP_SERVER_PORT: int = int(os.getenv("MCP_SERVER_PORT", "8001"))
    MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")

    # Security & limits
    SQL_ROW_LIMIT: int = int(os.getenv("SQL_ROW_LIMIT", "1000"))
    SQL_QUERY_TIMEOUT_SECONDS: int = int(os.getenv("SQL_QUERY_TIMEOUT_SECONDS", "30"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "100"))

    # Storage paths
    DATA_DIR: Path = BASE_DIR / os.getenv("DATA_DIR", "data")
    SKILLS_DIR: Path = BASE_DIR / "skills"

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
