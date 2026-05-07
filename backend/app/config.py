from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/poi_game"
    google_client_id: str = ""
    google_client_secret: str = ""
    secret_key: str = "change-me-in-production"
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    poi_search_radius_meters: int = 150
    poi_max_candidates: int = 30
    h3_resolution: int = 9
    use_h3_dedup: bool = False
    # When true, only offer questions whose GPS probe lies in LOS_ANGELES_BBOX (see app.regions)
    restrict_gps_to_la: bool = True

    @field_validator("secret_key")
    @classmethod
    def secret_key_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SECRET_KEY must be set")
        return v

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters when ENVIRONMENT=production")
            if not self.google_client_id or not self.google_client_secret:
                raise ValueError("Google OAuth credentials are required when ENVIRONMENT=production")
        return self


settings = Settings()
