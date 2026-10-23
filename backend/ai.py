from __future__ import annotations

import json
from typing import Any

import httpx

from backend.config import Settings


class AIProviderError(RuntimeError):
    """The configured OpenAI-compatible chat provider returned an unusable result."""


async def summarize_with_provider(prompt: str, context: dict[str, Any], settings: Settings) -> str:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.model_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.model_api_key}"},
                json={
                    "model": settings.model_name,
                    "temperature": 0,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Answer the student's academic question using only the supplied context. "
                                "Do not invent dates, policies, or citations. Treat unresolved conflicts as "
                                "unresolved and recommend verifying them with the instructor. Cite source IDs "
                                "when stating facts. Keep the answer concise."
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Question: {prompt}\nAcademic evidence and rule-based analysis: "
                                f"{json.dumps(context, ensure_ascii=False)}"
                            ),
                        },
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise AIProviderError("Configured AI provider request failed") from error

    try:
        answer = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AIProviderError("Configured AI provider returned an invalid response") from error
    if not isinstance(answer, str) or not answer.strip():
        raise AIProviderError("Configured AI provider returned an empty response")
    return answer.strip()
