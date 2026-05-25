from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Literal


class Settings(BaseSettings):
    # LLM
    llm_provider: Literal["anthropic", "openai", "portkey", "gemini"] = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    portkey_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"  # Options: gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Kite
    kite_api_key: str = ""
    kite_api_secret: str = ""
    kite_access_token: str = ""

    # Database
    database_url: str = "sqlite:///./market_copilot.db"
    redis_url: str = "redis://localhost:6379"

    # App
    scan_interval_minutes: int = 30
    scan_enabled: bool = True  # Set to false to disable scheduled scans
    market_open_hour: int = 9
    market_close_hour: int = 16
    enable_dashboard: bool = False
    scan_universe: str = "nifty50"  # nifty30, nifty50, nifty100, nifty200
    momentum_threshold: int = 3  # Minimum momentum score (1-5) to include
    auto_debate: bool = True  # Auto-run debate on top picks
    auto_debate_top_n: int = 2  # How many top stocks to auto-debate
    auto_debate_min_score: int = 4  # Minimum momentum score to trigger auto-debate

    class Config:
        env_file = ".env"

    @model_validator(mode="after")
    def decrypt_secrets(self):
        """Auto-decrypt any ENC: prefixed values."""
        from app.utils import decrypt_value, is_encrypted
        for field_name in [
            "anthropic_api_key", "openai_api_key", "portkey_api_key", "gemini_api_key",
            "telegram_bot_token", "telegram_chat_id",
            "kite_api_key", "kite_api_secret", "kite_access_token",
        ]:
            value = getattr(self, field_name, "")
            if value and is_encrypted(value):
                object.__setattr__(self, field_name, decrypt_value(value))
        return self


settings = Settings()
