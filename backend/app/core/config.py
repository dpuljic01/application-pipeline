from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "dev"
    DATABASE_URL: str
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str

    LLM_ENABLED: bool = True
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    CEREBRAS_API_KEY: str | None = None

    ADZUNA_APP_ID: str | None = None
    ADZUNA_APP_KEY: str | None = None
    ADZUNA_COUNTRY: str = "ch"

    @property
    def cognito_issuer(self) -> str:
        # Concept: issuer is used to validate `iss` claim in JWT
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}"

    @property
    def cognito_jwks_url(self) -> str:
        # Concept: JWKS endpoint publishes public keys for JWT signature verification
        return f"{self.cognito_issuer}/.well-known/jwks.json"


settings = Settings()
