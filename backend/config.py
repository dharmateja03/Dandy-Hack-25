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

    # LLM Configuration (Free Tier Models)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"  # Gemini 2.0 Flash (free tier)
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"  # Latest embedding model (free)

    # Slack Configuration
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_APP_TOKEN: Optional[str] = None

    # Jira Configuration (optional)
    JIRA_URL: Optional[str] = None
    JIRA_EMAIL: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None

    # GitHub Configuration
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_ORG: Optional[str] = None
    GITHUB_REPOS: Optional[str] = None  # Comma-separated list

    # Linear Configuration
    LINEAR_API_KEY: Optional[str] = None
    LINEAR_TEAM_ID: Optional[str] = None

    # Google Calendar Configuration
    GOOGLE_CALENDAR_CREDENTIALS: Optional[str] = None
    GOOGLE_CALENDAR_TOKEN: Optional[str] = None

    # Scheduling
    STANDUP_TIME: str = "09:00"  # 9 AM daily
    REMINDER_INTERVAL_HOURS: int = 6

    # Feature Flags
    ENABLE_JIRA_SYNC: bool = False
    ENABLE_GITHUB_SYNC: bool = False
    ENABLE_LINEAR_SYNC: bool = False
    ENABLE_CALENDAR_SYNC: bool = False
    ENABLE_VOICE: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
