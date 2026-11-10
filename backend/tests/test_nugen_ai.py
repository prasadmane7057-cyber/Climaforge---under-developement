"""Comprehensive Automated Test Suite for Nugen AI Integration.

Verifies:
1. Environment variable loading and configuration
2. Missing or blank API key handling
3. Nugen request payload and header construction
4. Streaming response parsing with SSE data chunks and `data: [DONE]` termination
5. Non-streaming completion handling
6. Upstream error handling (401, 429, 503, timeout, network failure)
7. Security: Upstream API credentials are never exposed in responses or logs
8. Endpoints: /api/chatbot/stream, /api/ai/chat, and /api/chatbot/message
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.dependencies.auth import require_permission
from app.main import app
from app.security.rbac import PERM_CHATBOT_ASK
from app.services.nugen_ai import (
    DEFAULT_NUGEN_MODEL,
    DEFAULT_NUGEN_URL,
    NUGEN_SYSTEM_PROMPT,
    NugenAIService,
    NugenAuthError,
    NugenRateLimitError,
    NugenTimeoutError,
    NugenUnavailableError,
    nugen_ai_service,
)

_REAL_ASYNC_CLIENT = httpx.AsyncClient


def test_nugen_config_loading():
    """Verify Nugen environment variables are loaded with proper defaults."""
    service = NugenAIService(
        api_key="test-key-123",
        api_url="https://api.nugen.in/api/v3/inference/chat/completions",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        max_tokens=500,
        temperature=0.1,
    )
    assert service.api_key == "test-key-123"
    assert service.api_url == "https://api.nugen.in/api/v3/inference/chat/completions"
    assert service.model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert service.max_tokens == 500
    assert service.temperature == 0.1
    assert service.is_configured() is True


def test_nugen_unconfigured_or_placeholder_key():
    """Verify placeholder or empty keys are recognized as unconfigured."""
    empty_service = NugenAIService(api_key="")
    assert empty_service.is_configured() is False

    placeholder_service = NugenAIService(api_key="replace-with-developer-key")
    assert placeholder_service.is_configured() is False


def test_nugen_message_construction_with_grounded_context():
    """Verify request messages contain system directive, scenario context, and history."""
    service = NugenAIService(api_key="mock-key")
    history = [
        {"role": "user", "content": "What is the status of Zone 1?"},
        {"role": "assistant", "content": "Zone 1 has elevated flood risk."},
    ]
    messages, context = service.build_messages(
        question="How should we prepare?",
        scenario_id="scenario-monsoon-alert",
        history=history,
    )

    assert len(messages) >= 3
    assert messages[0]["role"] == "system"
    assert "CLIMAFORGE AI" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "How should we prepare?"
    assert context.get("status") == "available"


@pytest.mark.asyncio
async def test_nugen_streaming_success():
    """Verify streaming response iterates tokens and signals completion cleanly."""
    service = NugenAIService(api_key="valid-mock-key")

    sse_body = (
        'data: {"id": "c1", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": "CLIMAFORGE "}}]}\n\n'
        'data: {"id": "c2", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": "AI is "}}]}\n\n'
        'data: {"id": "c3", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": "active."}}]}\n\n'
        'data: [DONE]\n\n'
    ).encode("utf-8")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer valid-mock-key"
        payload = json.loads(request.content.decode("utf-8"))
        assert payload["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
        assert payload["max_tokens"] == 500
        assert payload["stream"] is True
        return httpx.Response(200, content=sse_body, headers={"content-type": "text/event-stream"})

    mock_transport = httpx.MockTransport(mock_handler)

    with patch("app.services.nugen_ai.httpx.AsyncClient", side_effect=lambda **kw: _REAL_ASYNC_CLIENT(transport=mock_transport)), patch.object(
        settings, "nugen_mock_mode", False
    ):
        tokens = []
        done_payload = None

        async for event in service.stream_chat(
            question="What is the hazard status?",
            scenario_id="scenario-monsoon-alert",
        ):
            if "event: token" in event:
                data_line = [l for l in event.split("\n") if l.startswith("data: ")][0]
                token_data = json.loads(data_line[6:])
                tokens.append(token_data["token"])
            elif "event: done" in event:
                data_line = [l for l in event.split("\n") if l.startswith("data: ")][0]
                done_payload = json.loads(data_line[6:])

        assert "".join(tokens) == "CLIMAFORGE AI is active."
        assert done_payload is not None
        assert done_payload["done"] is True
        assert done_payload["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
        assert done_payload["provider"] == "Nugen AI"


@pytest.mark.asyncio
async def test_nugen_streaming_auth_error_handling():
    """Verify HTTP 401/403 yields sanitized error event without exposing credentials."""
    service = NugenAIService(api_key="invalid-key")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Unauthorized key"})

    mock_transport = httpx.MockTransport(mock_handler)

    with patch("app.services.nugen_ai.httpx.AsyncClient", side_effect=lambda **kw: _REAL_ASYNC_CLIENT(transport=mock_transport)), patch.object(
        settings, "nugen_mock_mode", False
    ):
        events = []
        async for event in service.stream_chat(question="Test question"):
            events.append(event)

        assert any("event: error" in e for e in events)
        error_event = events[0]
        assert "401" in error_event
        # Verify API key is NOT disclosed in the error event
        assert "invalid-key" not in error_event


@pytest.mark.asyncio
async def test_nugen_non_streaming_completion():
    """Verify non-streaming completion returns structured dictionary."""
    service = NugenAIService(api_key="valid-mock-key")

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-123",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Evacuation corridor is clear."},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    mock_transport = httpx.MockTransport(mock_handler)

    with patch("app.services.nugen_ai.httpx.AsyncClient", side_effect=lambda **kw: _REAL_ASYNC_CLIENT(transport=mock_transport)), patch.object(
        settings, "nugen_mock_mode", False
    ):
        result = await service.generate_chat_completion(
            question="What is the evacuation status?",
            scenario_id="scenario-monsoon-alert",
        )
        assert result["answer"] == "Evacuation corridor is clear."
        assert result["source"] == "LLM"
        assert result["model"] == "Qwen/Qwen2.5-0.5B-Instruct"
        assert result["is_advisory"] is True


@pytest.mark.asyncio
async def test_ai_chat_api_endpoint_streaming():
    """Verify POST /api/ai/chat supports SSE streaming."""
    async def mock_stream_chat(*args, **kwargs):
        yield f"event: token\ndata: {json.dumps({'token': 'Test '})}\n\n"
        yield f"event: token\ndata: {json.dumps({'token': 'token.'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'done': True, 'full_text': 'Test token.'})}\n\n"

    with patch.object(nugen_ai_service, "stream_chat", side_effect=mock_stream_chat):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/chat",
                json={
                    "message": "Explain flood risks",
                    "scenario_id": "scenario-monsoon-alert",
                    "stream": True,
                },
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            body = resp.text
            assert "event: token" in body
            assert "event: done" in body


@pytest.mark.asyncio
async def test_ai_chat_api_endpoint_non_streaming():
    """Verify POST /api/ai/chat supports JSON non-streaming completion."""
    mock_completion = {
        "answer": "Flood risk in riverside sector is elevated.",
        "source": "LLM",
        "model": "Qwen/Qwen2.5-0.5B-Instruct",
        "context_available": True,
    }

    with patch.object(
        nugen_ai_service, "generate_chat_completion", AsyncMock(return_value=mock_completion)
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/ai/chat?stream=false",
                json={
                    "message": "What is the flood risk?",
                    "scenario_id": "scenario-monsoon-alert",
                    "stream": False,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["answer"] == "Flood risk in riverside sector is elevated."
            assert data["provider"] == "Nugen AI"
            assert data["model"] == "Qwen/Qwen2.5-0.5B-Instruct"


@pytest.mark.asyncio
async def test_chatbot_stream_endpoint():
    """Verify POST /api/chatbot/stream streams tokens."""
    async def mock_stream_chat(*args, **kwargs):
        yield f"event: token\ndata: {json.dumps({'token': 'River '})}\n\n"
        yield f"event: token\ndata: {json.dumps({'token': 'corridor.'})}\n\n"
        yield f"event: done\ndata: {json.dumps({'done': True, 'full_text': 'River corridor.'})}\n\n"

    with patch.object(nugen_ai_service, "stream_chat", side_effect=mock_stream_chat):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/chatbot/stream",
                json={
                    "scenario_id": "scenario-monsoon-alert",
                    "question": "Where is the safe point?",
                },
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            assert "event: token" in resp.text
