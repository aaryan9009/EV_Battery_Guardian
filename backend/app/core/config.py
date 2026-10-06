from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """All secrets come from environment / .env, never from source code."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str                       # e.g. postgresql+psycopg2://user:pass@localhost:5432/ev_guardian
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:5173"
    model_dir: str = "model_store"
    max_upload_mb: int = 10
    admin_emails: str = ""                  # comma-separated; these emails get role=admin on register

def get_settings() -> Settings: return Settings()
