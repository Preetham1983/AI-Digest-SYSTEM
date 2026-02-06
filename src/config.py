from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import DirectoryPath, Field
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # System
    LOG_LEVEL: str = "INFO"
    DATA_DIR: Path = Path("./data")

    # Personas
    PERSONA_GENAI_NEWS_ENABLED: bool = True
    PERSONA_PRODUCT_IDEAS_ENABLED: bool = True
    PERSONA_FINANCE_ENABLED: bool = True

    # LLM
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"

    # Thresholds (previously hardcoded)
    GENAI_NEWS_MIN_RELEVANCE: float = 0.6
    PRODUCT_IDEAS_MIN_REUSABILITY: float = 0.5
    SEMANTIC_THRESHOLD: float = 0.15  # Evaluator pre-filter (very lenient)
    PREFILTER_THRESHOLD: float = 0.35  # Ingestion semantic prefilter
    HIGH_ENGAGEMENT_THRESHOLD: int = 100  # Raw score to bypass semantic filter
    TELEGRAM_CHUNK_SIZE: int = 4000  # Max chars per Telegram message

    # Email
    EMAIL_ENABLED: bool = False
    EMAIL_SMTP_HOST: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 465 # Default to SSL for Gmail
    EMAIL_TIMEOUT: int = 180 # Increased timeout
    EMAIL_FROM: str | None = None
    EMAIL_TO: str | None = None
    EMAIL_PASSWORD: str | None = None

    # Telegram
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    def ensure_dirs(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
