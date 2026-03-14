from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    vespa_url: str = "http://localhost:8080"
    default_namespace: str = "default"
    log_level: str = "INFO"

    model_config = {"env_prefix": "SB_"}
