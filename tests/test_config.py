import pytest

from backend.config import Settings


def test_configuration_rejects_example_placeholders(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "demo")
    monkeypatch.setenv("APP_PASSWORD", "replace-with-a-long-unique-demo-password")
    monkeypatch.setenv("SESSION_SECRET", "replace-with-at-least-32-random-characters")
    monkeypatch.setenv("MCP_BEARER_TOKEN", "replace-with-at-least-32-random-characters")
    with pytest.raises(ValueError, match="APP_PASSWORD"):
        Settings.from_env()


def test_configuration_accepts_non_placeholder_credentials(monkeypatch):
    monkeypatch.setenv("APP_USERNAME", "demo")
    monkeypatch.setenv("APP_PASSWORD", "unique-demo-password-1234")
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret-0123456789abcdef")
    monkeypatch.setenv("MCP_BEARER_TOKEN", "test-mcp-token-0123456789abcdef0123")
    configuration = Settings.from_env()
    assert configuration.username == "demo"
