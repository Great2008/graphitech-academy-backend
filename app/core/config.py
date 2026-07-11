"""
app/core/config.py

Settings loaded from environment variables (.env locally, Render env vars
in production). Never commit a real .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://user:password@localhost:5432/graphitech_academy"

    # --- Auth ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- AI ---
    GROQ_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # --- Payments ---
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""

    # --- Storage (Supabase) ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "graphitech-academy"

    # --- Coding playground ---
    PISTON_API_URL: str = "https://emkc.org/api/v2/piston"
    # Legacy Judge0 settings, kept in case of a future switch to self-hosted Judge0.
    JUDGE0_API_URL: str = ""
    JUDGE0_API_KEY: str = ""

    # --- Free-tier AI tutor rate limit ---
    TUTOR_FREE_DAILY_LIMIT: int = 15
    TUTOR_SUBSCRIPTION_PRICE_KOBO: int = 200000  # NGN 2,000/month — adjust as pricing is finalized

    # --- App ---
    ENVIRONMENT: str = "development"
    FRONTEND_URL: str = "http://localhost:5173"
    # Comma-separated list of additional allowed origins (e.g. custom domain,
    # mobile app webview origin). FRONTEND_URL is always included automatically.
    ADDITIONAL_CORS_ORIGINS: str = ""


settings = Settings()
