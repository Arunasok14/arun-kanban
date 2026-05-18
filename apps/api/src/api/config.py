import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default DB lives in the project root's /data directory
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
_DEFAULT_DB = os.path.join(_PROJECT_ROOT, "data", "kanban.db")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"file:{_DEFAULT_DB}"
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    runtime_manager_url: str = "http://localhost:8001"
    redis_url: str = "redis://localhost:6379"

    @property
    def db_path(self) -> str:
        url = self.database_url
        if url.startswith("file:"):
            return url[5:]
        return url


settings = Settings()
