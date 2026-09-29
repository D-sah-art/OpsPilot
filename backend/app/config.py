from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    app_name: str = "OpsPilot"
    environment: str = "development"
    port: int = 8080
    host: str = "0.0.0.0"
    
    # External ShopFlow Environment
    shopflow_base_url: str = Field(default="http://127.0.0.1:8000", validation_alias="SHOPFLOW_BASE_URL")
    shopflow_timeout_seconds: float = Field(default=5.0, validation_alias="SHOPFLOW_TIMEOUT_SECONDS")
    
    # SQLite Database
    database_url: str = Field(default="sqlite:///./opspilot.db", validation_alias="DATABASE_URL")

    # LLM Root-Cause Analysis Configuration (OpenAI-compatible)
    llm_api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4o-mini", validation_alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=15.0, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_temperature: float = Field(default=0.1, validation_alias="LLM_TEMPERATURE")

    # Remediation Configuration
    remediation_allowlist_path: str = Field(default="config/remediation_allowlist.yaml", validation_alias="REMEDIATION_ALLOWLIST_PATH")
    remediation_enabled: bool = Field(default=True, validation_alias="REMEDIATION_ENABLED")
    remediation_simulation_mode: bool = Field(default=True, validation_alias="REMEDIATION_SIMULATION_MODE")

    # Grafana Observability Source (Optional / Read-Only Discovery)
    grafana_url: str = Field(default="http://127.0.0.1:3000", validation_alias="GRAFANA_URL")
    grafana_api_key: Optional[str] = Field(default=None, validation_alias="GRAFANA_API_KEY")
    grafana_timeout_seconds: float = Field(default=2.0, validation_alias="GRAFANA_TIMEOUT_SECONDS")
    grafana_enabled: bool = Field(default=True, validation_alias="GRAFANA_ENABLED")

    # Hindsight Memory System Configuration (Vectorize)
    hindsight_base_url: str = Field(default="http://127.0.0.1:8080/hindsight", validation_alias="HINDSIGHT_BASE_URL")
    hindsight_api_key: Optional[str] = Field(default=None, validation_alias="HINDSIGHT_API_KEY")
    hindsight_bank_id: str = Field(default="opspilot-incidents-bank", validation_alias="HINDSIGHT_BANK_ID")
    hindsight_enabled: bool = Field(default=True, validation_alias="HINDSIGHT_ENABLED")
    hindsight_timeout_seconds: float = Field(default=5.0, validation_alias="HINDSIGHT_TIMEOUT_SECONDS")


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore"
    )

settings = Settings()
