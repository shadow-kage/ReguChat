from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    groq_api_key: str = ""
    hf_token: str = ""

    gemini_flash_model: str = "gemini-2.5-flash"
    groq_fallback_model: str = "llama-3.3-70b-versatile"

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 86_400

    domains_dir: str = "domains"

    # Comma-separated list of origins the browser is allowed to reach the API from.
    # In Docker the frontend nginx proxy makes CORS unnecessary, but it's required
    # for the Vite dev server (port 5173) talking directly to uvicorn (port 8000).
    cors_allowed_origins: str = "http://localhost:5173"


settings = Settings()
