import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    runtime_manager_port: int = 8001
    api_url: str = "http://localhost:8000"
    claude_bin: str = "/opt/homebrew/bin/claude"
    claude_model: str = "sonnet"
    claude_max_budget_usd: float = 2.00
    workspaces_root: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../../../workspaces",
    )
    redis_url: str = "redis://localhost:6379"
    queue_poll_interval: float = 0.5  # seconds between queue polls
    docker_image: str = "kanban-agent:latest"
    docker_mem_limit: str = "2g"
    docker_cpu_quota: int = 50000  # 50% of one core


settings = Settings()
