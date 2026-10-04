from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """App configuration, loaded from backend/.env.

    Model/provider settings live here in isolation so they can be swapped
    later (different model, different Backboard base URL) without touching
    any request-handling or prompting logic elsewhere in the app.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    backboard_api_key: str = ""
    backboard_base_url: str = "https://app.backboard.io/api"
    # Backboard doesn't expose a literal "kimi-k2.6" model; this alias always
    # points at the latest model in the Kimi family, served via openrouter.
    backboard_model: str = "~moonshotai/kimi-latest"
    backboard_llm_provider: str = "openrouter"
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
