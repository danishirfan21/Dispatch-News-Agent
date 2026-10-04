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

    serpapi_api_key: str = ""
    serpapi_base_url: str = "https://serpapi.com/search"
    # Kept small deliberately: SerpApi's free plan has a limited monthly quota.
    serpapi_results_per_interest: int = 4

    frontend_origin: str = "http://localhost:5173"

    mongodb_uri: str = ""
    mongodb_db_name: str = "dispatch"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 14

    # Flip to true behind HTTPS in production so the auth cookie requires it.
    cookie_secure: bool = False


settings = Settings()
