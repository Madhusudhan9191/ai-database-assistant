from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    groq_api_key: str
    jwt_secret: str = "ai-database-assistant-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry: int = 60

    # Default DB environment credentials
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ai_database_assistant"
    db_user: str = "ai_readonly"
    db_password: str = "readonly123"

    # CORS configurations
    cors_origins: str = "http://localhost:5173"

    # Deployment & Metadata
    app_version: str = "1.0.0"
    environment: str = "development"

    # Admin Seeding
    admin_username: str = ""
    admin_email: str = ""
    admin_password: str = ""

    # Settings configuration to look for .env file and ignore extra variables
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
