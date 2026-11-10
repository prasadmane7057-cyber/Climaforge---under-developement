"""CLIMAFORGE Nugen AI Integration Service.

Provides asynchronous, streaming conversational AI capabilities powered by Nugen AI
(Qwen/Qwen2.5-0.5B-Instruct) for climate-risk decision support, disaster management,
and evacuation intelligence.

Strict Safety Rules:
- Never exposes upstream API keys, credentials, or sensitive headers.
- Algorithms 0–13 remain completely authoritative.
- Distinguishes general conversational advice from authoritative scenario calculations.
- Closes HTTP streaming connections cleanly on client disconnects.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.chatbot import build_grounded_context, deterministic_fallback
from app.config import settings

logger = logging.getLogger("climaforge.nugen_ai")

# Canonical System Prompt for CLIMAFORGE AI
NUGEN_SYSTEM_PROMPT = (
    "You are CLIMAFORGE AI, an intelligent climate-risk and disaster-management assistant. "
    "You provide clear, accurate guidance on climate hazards, flood risks, disaster preparedness, "
    "and emergency evacuation procedures. "
    "When answering questions about the current CLIMAFORGE scenario, rely strictly on the authoritative "
    "deterministic analysis and data provided in the context JSON. "
    "Do not invent unverified live sensor readings, flood gauges, emergency alerts, casualties, or infrastructure status. "
    "Clearly distinguish general climate science and preparedness guidance from scenario-specific deterministic calculations. "
    "Algorithms 0–13 calculations remain authoritative. Recommendations are advisory and require verification by qualified personnel."
)

DEFAULT_NUGEN_URL = "https://api.nugen.in/api/v3/inference/chat/completions"
DEFAULT_NUGEN_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


class NugenAIError(Exception):
    """Base exception for Nugen AI operations."""
    def __init__(self, message: str, status_code: int = 500, error_type: str = "upstream_error") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type


class NugenAuthError(NugenAIError):
    """Raised when Nugen API rejects credentials."""
    def __init__(self, message: str = "Authentication with Nugen AI failed.") -> None:
        super().__init__(message, status_code=401, error_type="auth_error")


class NugenRateLimitError(NugenAIError):
    """Raised when upstream rate limit is hit."""
    def __init__(self, message: str = "Nugen AI rate limit reached. Please wait and retry.") -> None:
        super().__init__(message, status_code=429, error_type="rate_limit")


class NugenUnavailableError(NugenAIError):
    """Raised when Nugen service is temporarily offline or returns 5xx."""
    def __init__(self, message: str = "Nugen AI service is temporarily unavailable.") -> None:
        super().__init__(message, status_code=503, error_type="service_unavailable")


class NugenTimeoutError(NugenAIError):
    """Raised on inference request timeout."""
    def __init__(self, message: str = "Nugen AI request timed out.") -> None:
        super().__init__(message, status_code=504, error_type="timeout")


class NugenAIService:
    """Dedicated service for Nugen AI streaming and completion requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self._api_key = api_key
        self._api_url = api_url
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout_seconds = timeout_seconds

    @property
    def api_key(self) -> str:
        if self._api_key is not None:
            return self._api_key.strip()
        key = settings.nugen_api_key or settings.chatbot_api_key or ""
        return key.strip()

    @property
    def api_url(self) -> str:
        url = self._api_url or settings.nugen_api_url or settings.nugen_endpoint or DEFAULT_NUGEN_URL
        return url.strip()

    @property
    def model(self) -> str:
        return (self._model or settings.nugen_model or DEFAULT_NUGEN_MODEL).strip()

    @property
    def max_tokens(self) -> int:
        return self._max_tokens or getattr(settings, "nugen_max_tokens", 500) or 500

    @property
    def temperature(self) -> float:
        return self._temperature if self._temperature is not None else getattr(settings, "nugen_temperature", 0.1)

    @property
    def timeout_seconds(self) -> float:
        return self._timeout_seconds or settings.nugen_timeout_seconds or 25.0

    def is_configured(self) -> bool:
        """Verify whether an active, non-placeholder API key is configured."""
        key = self.api_key
        if not key:
            return False
        lower = key.lower()
        if lower.startswith("replace") or lower.startswith("your") or lower.startswith("<"):
            return False
        return True

    def build_messages(
        self,
        question: str,
        scenario_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[List[Dict[str, str]], Dict[str, Any]]:
        """Construct the prompt messages array including system directives and grounded context."""
        context: Dict[str, Any] = {}
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": NUGEN_SYSTEM_PROMPT}
        ]

        # Attach deterministic scenario context if scenario_id is provided
        if scenario_id:
            context = build_grounded_context(scenario_id, question)
            if context.get("status") == "available":
                context_str = json.dumps(
                    context,
                    default=str,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                messages.append({
                    "role": "system",
                    "content": f"Authoritative CLIMAFORGE Scenario Context JSON:\n{context_str[:16000]}",
                })

        # Append sanitized history
        if history:
            for item in history[-12:]:
                role = item.get("role")
                content = (item.get("content") or "").strip()
                if role in {"user", "assistant"} and content:
                    messages.append({"role": role, "content": content[:2000]})

        # Append current user question
        messages.append({"role": "user", "content": question.strip()[:2000]})
        return messages, context

    async def stream_chat(
        self,
        question: str,
        scenario_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Stream conversational tokens from Nugen AI via Server-Sent Events (SSE).

        Yields SSE formatted strings:
        - `event: token\\ndata: {\"token\": \"...\"}\\n\\n`
        - `event: done\\ndata: {\"done\": true, \"full_text\": \"...\", \"model\": \"...\"}\\n\\n`
        - `event: error\\ndata: {\"error\": \"...\", \"fallback\": \"...\"}\\n\\n`
        """
        # Validate question
        if not question or not question.strip():
            err_data = json.dumps({"error": "Question cannot be blank.", "done": True})
            yield f"event: error\ndata: {err_data}\n\n"
            return

        messages, context = self.build_messages(question, scenario_id, history)

        # If Nugen is unconfigured or mock mode is active, yield deterministic response
        if not self.is_configured() or settings.nugen_mock_mode:
            logger.info("Nugen API unconfigured or mock mode active; streaming deterministic fallback.")
            fallback_text = deterministic_fallback(question, context) if context else (
                "CLIMAFORGE AI is running in offline mode. Nugen API credentials are not configured. "
                "Deterministic decision algorithms and risk metrics remain active."
            )
            # Yield full response in a couple of simulated chunks for smooth UI UX
            words = fallback_text.split(" ")
            chunk_size = 4
            for i in range(0, len(words), chunk_size):
                token_chunk = " ".join(words[i : i + chunk_size]) + " "
                yield f"event: token\ndata: {json.dumps({'token': token_chunk})}\n\n"
            yield f"event: done\ndata: {json.dumps({'done': True, 'full_text': fallback_text, 'source': 'DETERMINISTIC_FALLBACK', 'model': 'offline-engine'})}\n\n"
            return

        payload = {
            "max_tokens": self.max_tokens,
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
        }

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CLIMAFORGE-Advisory-Client/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        full_text = ""
        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", self.api_url, json=payload, headers=headers) as resp:
                    if resp.status_code == 401 or resp.status_code == 403:
                        logger.error("Nugen API rejected authorization token (HTTP %d).", resp.status_code)
                        err_msg = "Authentication with Nugen AI failed. Please verify API key configuration."
                        yield f"event: error\ndata: {json.dumps({'error': err_msg, 'status_code': 401})}\n\n"
                        return

                    if resp.status_code == 429:
                        logger.warning("Nugen AI upstream rate limit exceeded (HTTP 429).")
                        err_msg = "Nugen AI rate limit reached. Please wait a moment and retry."
                        yield f"event: error\ndata: {json.dumps({'error': err_msg, 'status_code': 429})}\n\n"
                        return

                    if resp.status_code >= 500:
                        logger.error("Nugen AI upstream returned 5xx error (HTTP %d).", resp.status_code)
                        err_msg = "Nugen AI inference service is temporarily unavailable. Please retry shortly."
                        yield f"event: error\ndata: {json.dumps({'error': err_msg, 'status_code': 503})}\n\n"
                        return

                    if resp.status_code != 200:
                        logger.error("Nugen AI unexpected HTTP %d response.", resp.status_code)
                        err_msg = f"Nugen AI returned unexpected response (HTTP {resp.status_code})."
                        yield f"event: error\ndata: {json.dumps({'error': err_msg, 'status_code': resp.status_code})}\n\n"
                        return

                    # Parse Server-Sent Events from Nugen
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue

                        # Handle Stream Termination marker
                        if line == "data: [DONE]":
                            break

                        if line.startswith("data: "):
                            raw_json = line[6:].strip()
                            try:
                                chunk = json.loads(raw_json)
                            except json.JSONDecodeError:
                                continue

                            choices = chunk.get("choices")
                            if choices and isinstance(choices, list):
                                first_choice = choices[0]
                                delta = first_choice.get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    full_text += token
                                    yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

            # Stream completed successfully
            done_payload = {
                "done": True,
                "full_text": full_text.strip(),
                "model": self.model,
                "provider": "Nugen AI",
                "source": "LLM",
                "is_advisory": True,
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        except httpx.TimeoutException as exc:
            logger.warning("Nugen AI streaming timed out: %s", exc)
            err_data = json.dumps({"error": "Nugen AI inference timed out. Please retry.", "type": "timeout"})
            yield f"event: error\ndata: {err_data}\n\n"
        except httpx.RequestError as exc:
            logger.warning("Nugen AI network connection failed: %s", exc)
            err_data = json.dumps({"error": "Network connection to Nugen AI failed.", "type": "network"})
            yield f"event: error\ndata: {err_data}\n\n"
        except Exception as exc:
            logger.error("Unexpected error during Nugen AI streaming: %s", exc)
            err_data = json.dumps({"error": "An unexpected error occurred while generating response.", "type": "unknown"})
            yield f"event: error\ndata: {err_data}\n\n"

    async def generate_chat_completion(
        self,
        question: str,
        scenario_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Generate a complete non-streaming chat completion from Nugen AI."""
        if not question or not question.strip():
            raise NugenAIError("Question cannot be blank.", status_code=400, error_type="validation_error")

        messages, context = self.build_messages(question, scenario_id, history)

        if not self.is_configured() or settings.nugen_mock_mode:
            fallback = deterministic_fallback(question, context) if context else (
                "CLIMAFORGE AI is running in offline mode. Nugen API credentials are not configured."
            )
            return {
                "answer": fallback,
                "source": "DETERMINISTIC_FALLBACK",
                "mode": "deterministic_fallback",
                "scenario_id": scenario_id or "",
                "context_available": context.get("status") == "available" if context else False,
                "model": "offline-engine",
                "is_advisory": True,
            }

        payload = {
            "max_tokens": self.max_tokens,
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": self.temperature,
        }

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CLIMAFORGE-Advisory-Client/1.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        timeout = httpx.Timeout(self.timeout_seconds, connect=10.0)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(self.api_url, json=payload, headers=headers)

                if resp.status_code == 401 or resp.status_code == 403:
                    raise NugenAuthError()
                if resp.status_code == 429:
                    raise NugenRateLimitError()
                if resp.status_code >= 500:
                    raise NugenUnavailableError()
                if resp.status_code != 200:
                    raise NugenAIError(f"Nugen AI returned HTTP {resp.status_code}", status_code=resp.status_code)

                data = resp.json()
                choices = data.get("choices", [])
                if not choices or not isinstance(choices, list):
                    raise NugenAIError("Invalid choices structure returned by Nugen AI")

                content = choices[0].get("message", {}).get("content", "")
                if not content or not content.strip():
                    raise NugenAIError("Empty content received from Nugen AI")

                return {
                    "answer": content.strip(),
                    "source": "LLM",
                    "mode": "grounded_llm",
                    "scenario_id": scenario_id or "",
                    "context_available": context.get("status") == "available" if context else False,
                    "model": self.model,
                    "is_advisory": True,
                }

        except httpx.TimeoutException as exc:
            raise NugenTimeoutError() from exc
        except httpx.RequestError as exc:
            raise NugenAIError("Network request to Nugen AI failed", status_code=502, error_type="network_error") from exc


# Global service singleton
nugen_ai_service = NugenAIService()
