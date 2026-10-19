from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    anthropic_api_key: str = ""
    database_path: str = "backend/data/internmatch.db"
    cors_origins: str = ""
    ingest_timezone: str = "America/Los_Angeles"
    enable_admin_routes: bool = False

    @property
    def db_file(self) -> Path:
        # Relative paths in .env are written from the repo root, not the backend folder.
        path = Path(self.database_path)
        return path if path.is_absolute() else REPO_ROOT / path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
