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
    # Max candidates shown per question. Kept small: long option lists in
    # dense areas dilute agreement and overload annotators.
    poi_max_candidates: int = 12
    h3_resolution: int = 9
    use_h3_dedup: bool = True

    # Consensus policy. A question collects consensus_base_target independent
    # answers; if annotators disagree, or the area is dense
    # (candidate_density >= dense_candidate_threshold), the target escalates
    # to consensus_max_target before the label is finalized.
    consensus_base_target: int = 3
    consensus_max_target: int = 5
    dense_candidate_threshold: int = 12
    # Sybil gate: answers from accounts younger than this don't count toward
    # consensus (they still earn participation points). 0 disables the gate;
    # set to e.g. 60 in production.
    consensus_min_account_age_minutes: int = 0
    # When true, only offer questions whose GPS probe lies in LOS_ANGELES_BBOX (see app.regions)
    restrict_gps_to_la: bool = True

    @field_validator("secret_key")
    @classmethod
    def secret_key_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SECRET_KEY must be set")
        return v

    @field_validator("frontend_url", "backend_url")
    @classmethod
    def strip_trailing_slash(cls, v: str) -> str:
        # A trailing slash in FRONTEND_URL would break the exact-match CORS
        # origin check in main.py.
        return v.rstrip("/")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.environment.lower() == "production":
            if len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be at least 32 characters when ENVIRONMENT=production")
            if not self.google_client_id or not self.google_client_secret:
                raise ValueError("Google OAuth credentials are required when ENVIRONMENT=production")
        return self


settings = Settings()
