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
    # Global (all users) daily LLM spend cap, checked against llm_usage
    # before every call. None disables the check.
    LLM_DAILY_BUDGET_USD: float | None = 1.0

    # Shared demo account (a normal Cognito user). Both unset = the demo
    # login endpoint is disabled. Kept server-side so the password never
    # ships in the frontend bundle.
    DEMO_EMAIL: str | None = None
    DEMO_PASSWORD: str | None = None
    # The demo account's own daily LLM cap (USD), on top of the global one.
    LLM_DEMO_DAILY_BUDGET_USD: float = 0.25

    ADZUNA_APP_ID: str | None = None
    ADZUNA_APP_KEY: str | None = None
    ADZUNA_COUNTRY: str = "ch"

    # Comma-separated — was hardcoded to localhost only, which breaks the
    # moment the frontend is deployed anywhere real (Vercel, etc.)
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def cognito_issuer(self) -> str:
        # Concept: issuer is used to validate `iss` claim in JWT
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}"

    @property
    def cognito_jwks_url(self) -> str:
        # Concept: JWKS endpoint publishes public keys for JWT signature verification
        return f"{self.cognito_issuer}/.well-known/jwks.json"


settings = Settings()
