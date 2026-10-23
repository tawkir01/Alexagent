from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _required_secret(name: str, minimum_length: int = 32) -> str:
    value = os.getenv(name, "")
    if len(value) < minimum_length or value.lower().startswith("replace-with-"):
        raise ValueError(
            f"{name} must be replaced with a non-placeholder value of at least {minimum_length} characters"
        )
    return value


@dataclass(frozen=True)
class Settings:
    username: str
    password: str
    session_secret: str
    mcp_bearer_token: str
    model_api_key: str
    model_base_url: str
    model_name: str
    cookie_secure: bool
    host: str
    api_port: int
    mcp_host: str
    mcp_port: int
    database_url: str
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        username = os.getenv("APP_USERNAME", "")
        password = os.getenv("APP_PASSWORD", "")
        if not username or not password:
            raise ValueError("APP_USERNAME and APP_PASSWORD must be configured")
        if len(password) < 16 or password.lower().startswith("replace-with-"):
            raise ValueError("APP_PASSWORD must be replaced with a unique value of at least 16 characters")

        return cls(
            username=username,
            password=password,
            session_secret=_required_secret("SESSION_SECRET"),
            mcp_bearer_token=_required_secret("MCP_BEARER_TOKEN"),
            model_api_key=os.getenv("MODEL_API_KEY", ""),
            model_base_url=os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model_name=os.getenv("MODEL_NAME", "gpt-4o-mini"),
            cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
            host=os.getenv("HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8000")),
            mcp_host=os.getenv("MCP_HOST", "127.0.0.1"),
            mcp_port=int(os.getenv("MCP_PORT", "8001")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./campusflow.db"),
            allowed_origins=tuple(
                origin.strip().casefold().rstrip("/")
                for origin in os.getenv("APP_ALLOWED_ORIGINS", "").split(",")
                if origin.strip()
            ),
        )


settings = Settings.from_env()
