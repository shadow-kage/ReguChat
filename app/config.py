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


settings = Settings()
