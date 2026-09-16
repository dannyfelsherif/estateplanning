from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    session_secret_key: str = "change-me-to-a-long-random-value"

    database_url: str = "sqlite:///./data/estate.db"
    upload_dir: str = "./data/uploads"

    admin_email: str = "attorney@example.com"
    admin_password: str = "change-me-immediately"
    admin_name: str = "Firm Attorney"

    @property
    def mock_llm(self) -> bool:
        return not self.anthropic_api_key


settings = Settings()

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.database_url.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
