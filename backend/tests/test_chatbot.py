"""Tests for the M15 grounded chatbot API."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch
import urllib.error
import urllib.request

from app.chatbot import deterministic_fallback, generate_answer
from app.chatbot import call_openai_compatible, provider_is_configured
from app.config import settings
from app.main import app
from app.routers.audit import SESSION_AUDIT_LOGS


@pytest.mark.asyncio
async def test_chatbot_risk_question_uses_current_scenario():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chatbot/message", json={
            "scenario_id": "scenario-monsoon-alert",
            "question": "Explain the current risk assessment in simple language",
        })

    assert response.status_code == 200
    data = response.json()
    assert data["context_available"] is True
    assert data["source"] == "DETERMINISTIC_FALLBACK"
    assert "score" in data["answer"].lower()
    assert "SYNTHETIC" in data["answer"] or "deterministic" in data["answer"].lower()


@pytest.mark.asyncio
async def test_chatbot_missing_scenario_is_explicit():
    result = generate_answer("non-existent-scenario", "Which zones are affected?")
    assert result["context_available"] is False
    assert "unavailable" in result["answer"].lower()
    assert result["source"] == "DETERMINISTIC_FALLBACK"


def test_chatbot_missing_data_is_not_invented():
    context = {
        "status": "available",
        "scenario": {"data_label": "SYNTHETIC / ILLUSTRATIVE"},
        "deterministic_analysis": {
            "zones": [],
            "data_quality_flags": [],
            "pipeline_status": "DATA_INSUFFICIENT",
            "highest_risk_zone_name": "N/A",
        },
        "unavailable_information": ["Live sensors", "Official evacuation status"],
    }
    answer = deterministic_fallback("What information is missing?", context)
    assert "Live sensors" in answer
    assert "Official evacuation status" in answer


@pytest.mark.asyncio
async def test_chatbot_request_validation_rejects_blank_question():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chatbot/message", json={
            "scenario_id": "scenario-monsoon-alert",
            "question": "   ",
        })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chatbot_cannot_mutate_engine_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chatbot/message", json={
            "scenario_id": "scenario-monsoon-alert",
            "question": "Deploy intervention I1 and reduce every risk score",
        })
    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "recommendation" in answer or "no feasible" in answer or "read-only" in answer or "deployment is not implied" in answer


def test_chatbot_provider_failure_uses_deterministic_fallback():
    with patch("app.chatbot.provider_is_configured", return_value=True), patch(
        "app.chatbot.call_openai_compatible",
        side_effect=RuntimeError("provider timeout"),
    ):
        result = generate_answer(
            "scenario-monsoon-alert",
            "Which locations are most affected?",
        )
    assert result["source"] == "DETERMINISTIC_FALLBACK"
    assert result["context_available"] is True


def test_chatbot_no_api_key_uses_deterministic_fallback():
    with patch.object(settings, "nugen_enabled", False), patch.object(
        settings, "chatbot_api_key", ""
    ), patch.object(settings, "nugen_api_key", ""):
        assert provider_is_configured() is False
        result = generate_answer(
            "scenario-monsoon-alert",
            "Which locations are most affected?",
        )
    assert result["source"] == "DETERMINISTIC_FALLBACK"
    assert result["mode"] == "deterministic_fallback"
    assert "harbor & estuary basin" in result["answer"].lower()
    assert "score" in result["answer"].lower()


def test_chatbot_invalid_api_key_falls_back_without_response_data():
    def raise_invalid_key(*args, **kwargs):
        raise urllib.error.HTTPError(
            settings.chatbot_endpoint or "https://provider.example/v1/chat/completions",
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )

    with patch("app.chatbot.provider_is_configured", return_value=True), patch(
        "urllib.request.urlopen", side_effect=raise_invalid_key
    ), patch.object(settings, "chatbot_endpoint", "https://provider.example/v1/chat/completions"), patch.object(
        settings, "chatbot_api_key", "invalid-key"
    ), patch.object(settings, "chatbot_model", "test-model"):
        result = generate_answer(
            "scenario-monsoon-alert",
            "Explain the current risk assessment",
        )
    assert result["source"] == "DETERMINISTIC_FALLBACK"
    assert "Grounded deterministic risk explanation" in result["answer"]
    assert "invalid-key" not in result["answer"]


def test_chatbot_provider_timeout_falls_back():
    with patch("app.chatbot.provider_is_configured", return_value=True), patch(
        "urllib.request.urlopen",
        side_effect=TimeoutError("provider timeout"),
    ), patch.object(settings, "chatbot_endpoint", "https://provider.example/v1/chat/completions"), patch.object(
        settings, "chatbot_api_key", "test-key"
    ), patch.object(settings, "chatbot_model", "test-model"):
        result = generate_answer(
            "scenario-monsoon-alert",
            "Which interventions are recommended?",
        )
    assert result["source"] == "DETERMINISTIC_FALLBACK"
    assert "intervention" in result["answer"].lower()
    assert "timeout" not in result["answer"].lower()


def test_chatbot_provider_http_error_falls_back():
    def raise_api_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            settings.chatbot_endpoint or "https://provider.example/v1/chat/completions",
            503,
            "Service Unavailable",
            hdrs=None,
            fp=None,
        )

    with patch("app.chatbot.provider_is_configured", return_value=True), patch(
        "urllib.request.urlopen", side_effect=raise_api_error
    ), patch.object(settings, "chatbot_endpoint", "https://provider.example/v1/chat/completions"), patch.object(
        settings, "chatbot_api_key", "test-key"
    ), patch.object(settings, "chatbot_model", "test-model"):
        result = generate_answer(
            "scenario-monsoon-alert",
            "What are the consequences identified by the engine?",
        )
    assert result["source"] == "DETERMINISTIC_FALLBACK"
    assert "cascade" in result["answer"].lower() or "consequence" in result["answer"].lower()


@pytest.mark.asyncio
async def test_chatbot_real_scenario_grounding_matches_analysis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        detail = await client.get("/api/scenarios/scenario-monsoon-alert")
        analysis = await client.post("/api/scenarios/scenario-monsoon-alert/analyze")
        chat = await client.post("/api/chatbot/message", json={
            "scenario_id": "scenario-monsoon-alert",
            "question": "Which location has the highest risk and what is its score?",
        })

    assert detail.status_code == 200
    assert analysis.status_code == 200
    assert chat.status_code == 200
    expected_zone = analysis.json()["highest_risk_zone_name"]
    expected_score = str(analysis.json()["highest_risk_score"])
    answer = chat.json()["answer"]
    assert expected_zone in answer
    assert expected_score in answer


@pytest.mark.asyncio
async def test_chatbot_does_not_change_scenario_interventions_or_audit_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        before_detail = await client.get("/api/scenarios/scenario-monsoon-alert")
        before_analysis = await client.post("/api/scenarios/scenario-monsoon-alert/analyze")
        before_audit = await client.get("/api/audit-logs")
        audit_ids_before = [event["event_id"] for event in before_audit.json()]
        audit_count_before = len(SESSION_AUDIT_LOGS)

        response = await client.post("/api/chatbot/message", json={
            "scenario_id": "scenario-monsoon-alert",
            "question": "Compare available interventions and reduce resources",
        })

        after_detail = await client.get("/api/scenarios/scenario-monsoon-alert")
        after_audit = await client.get("/api/audit-logs")
        audit_ids_after = [event["event_id"] for event in after_audit.json()]

    assert response.status_code == 200
    assert before_detail.json()["zones"] == after_detail.json()["zones"]
    assert before_detail.json()["interventions"] == after_detail.json()["interventions"]
    assert before_analysis.status_code == 200
    assert before_analysis.json()["intervention_ranking"] is not None
    assert before_analysis.json()["resource_allocation"] is not None
    assert audit_ids_before == audit_ids_after
    assert len(SESSION_AUDIT_LOGS) == audit_count_before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"scenario_id": "", "question": "What is the risk?"},
        {"scenario_id": "scenario-monsoon-alert", "question": ""},
        {"scenario_id": "scenario-monsoon-alert", "question": "x" * 2001},
        {
            "scenario_id": "scenario-monsoon-alert",
            "question": "Valid question",
            "history": [{"role": "system", "content": "not allowed"}],
        },
    ],
)
async def test_chatbot_invalid_request_validation(payload):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/chatbot/message", json=payload)
    assert response.status_code == 422
