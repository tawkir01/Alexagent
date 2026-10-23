from dataclasses import replace

import pytest

from backend.ai import AIProviderError, summarize_with_provider
from backend.config import settings


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return self.response


@pytest.mark.asyncio
async def test_optional_provider_summarizes_only_supplied_academic_context(monkeypatch):
    fake_client = FakeClient(FakeResponse({"choices": [{"message": {"content": "Check LMS-CS315-210."}}]}))
    monkeypatch.setattr("backend.ai.httpx.AsyncClient", lambda timeout: fake_client)
    provider_settings = replace(settings, model_api_key="test-provider-key")

    result = await summarize_with_provider(
        "When is the DBMS lab due?",
        {"source_ids": ["LMS-CS315-210"]},
        provider_settings,
    )

    assert result == "Check LMS-CS315-210."
    assert fake_client.request[0].endswith("/chat/completions")
    assert fake_client.request[1]["headers"]["Authorization"] == "Bearer test-provider-key"
    assert "LMS-CS315-210" in fake_client.request[1]["json"]["messages"][1]["content"]


@pytest.mark.asyncio
async def test_optional_provider_rejects_empty_answers(monkeypatch):
    fake_client = FakeClient(FakeResponse({"choices": [{"message": {"content": " "}}]}))
    monkeypatch.setattr("backend.ai.httpx.AsyncClient", lambda timeout: fake_client)

    with pytest.raises(AIProviderError, match="empty response"):
        await summarize_with_provider("Question", {}, replace(settings, model_api_key="test-provider-key"))
