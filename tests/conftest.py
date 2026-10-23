import os

os.environ.setdefault("APP_USERNAME", "test-user")
os.environ.setdefault("APP_PASSWORD", "test-password-that-is-long-enough")
os.environ.setdefault("SESSION_SECRET", "test-session-secret-0123456789abcdef")
os.environ.setdefault("MCP_BEARER_TOKEN", "test-mcp-token-0123456789abcdef012345")
os.environ.setdefault("MODEL_API_KEY", "")

import pytest

from backend import academic
from backend.db import SessionLocal


@pytest.fixture(autouse=True)
def reset_synthetic_academic_data():
    with SessionLocal() as db:
        academic.reset_demo_data(db)
