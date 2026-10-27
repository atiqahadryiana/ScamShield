from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[3] / '.env', extra='ignore')
    database_url: str = 'sqlite:///./scamshield.db'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    environment: str = 'development'
    rate_limit_per_minute: int = 30
    telegram_bot_token: str = ''
    telegram_bot_username: str = ''
    telegram_webhook_url: str = ''
    telegram_webhook_secret: str = ''
    telegram_port: int = 8081
    tesseract_cmd: str = ''
    ocr_languages: str = 'eng'
    history_retention_days: int = 30
    ml_message_artifact: str = ''
    ml_message_report: str = ''
    ml_url_artifact: str = ''
    ml_url_report: str = ''
    phishtank_app_key: str = ''
    phishtank_user_agent: str = 'phishtank/scamshield-ai'


@lru_cache
def get_settings() -> Settings:
    return Settings()
