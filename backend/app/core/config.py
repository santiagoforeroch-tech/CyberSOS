from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./cybersos-dev.db"
    frontend_origin: str = "http://localhost:5173"
    supabase_service_role_key: str = ""
    whatsapp_session_encryption_key: str = ""
    whatsapp_webhook_secret: str | None = None
    whatsapp_bridge_url: str = "http://127.0.0.1:3001"
    whatsapp_admin_local: bool = True
    whatsapp_max_media_mb: int = 20
    session_secret: str = ""
    admin_setup_password: str = ""
    cookie_secure: bool = False
    retention_days: int = 90
    public_report_rate_limit: int = 5
    public_report_rate_window_seconds: int = 3600
    cron_secret: str = ""
    auth_provider: str = "local"
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_admin_email: str = ""
    local_admin_email: str = "admin@cybersos.example"
    local_admin_password: str = ""
    local_mfa_code: str = ""
    notifications_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_from: str = ""
    notification_admin_email: str = ""
    antivirus_enabled: bool = False
    clamav_host: str = "127.0.0.1"
    clamav_port: int = 3310
    clamav_timeout_seconds: int = 15
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    ai_provider: str = "gemini"
    ai_agent_enabled: bool = True
    ai_local_mode: bool = False
    ai_agent_max_history_messages: int = 20
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
