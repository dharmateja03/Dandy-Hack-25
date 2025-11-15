"""
Configuration settings for MCP
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_VERSION: str = "0.1.0"
    APP_NAME: str = "MCP - Model Context Protocol"

    # Database
    DATABASE_URL: str = "postgresql://mcp_user:mcp_password@postgres:5432/mcp_db"

    # Vector Database
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION_NAME: str = "mcp_context"
    EMBEDDING_DIMENSION: int = 768

    # LLM Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"

    # Slack Configuration
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None

    # Jira Configuration (optional)
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None

    # Scheduling
    STANDUP_TIME: str = "09:00"  # 9 AM daily
    REMINDER_INTERVAL_HOURS: int = 6

    # Feature Flags
    ENABLE_JIRA_SYNC: bool = False
    ENABLE_VOICE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
