"""CLIMAFORGE Dedicated AI Chat Router.

Provides `/ai/chat` endpoint supporting streaming and non-streaming responses
via Nugen AI for climate hazard explanations, evacuation recommendations,
and disaster preparedness queries.
"""

from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.dependencies.auth import require_permission
from app.security.rbac import PERM_CHATBOT_ASK
from app.services.nugen_ai import NugenAIError, nugen_ai_service


router = APIRouter(prefix="/ai", tags=["AI Conversational Assistant"])


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message content cannot be blank")
        return v.strip()


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question or inquiry")
    scenario_id: Optional[str] = Field(None, max_length=128, description="Scenario ID for deterministic grounding")
    history: List[AIChatMessage] = Field(default_factory=list, max_length=12, description="Prior conversation messages")
    stream: bool = Field(default=True, description="Whether to stream response tokens via SSE")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be blank")
        return v.strip()


class AIChatResponse(BaseModel):
    answer: str
    source: str = "LLM"
    model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    provider: str = "Nugen AI"
    scenario_id: str = ""
    context_available: bool = True
    is_advisory: bool = True


@router.post(
    "/chat",
    summary="Ask CLIMAFORGE AI (Streaming or JSON)",
    description="Stream or retrieve conversational climate-risk and disaster management answers from Nugen AI.",
    responses={
        200: {"description": "Streaming Server-Sent Events (SSE) or JSON Chat completion."},
        400: {"description": "Invalid user input or malformed request."},
        401: {"description": "Authentication failure with backend or upstream Nugen AI."},
        429: {"description": "Upstream rate limit reached."},
        503: {"description": "Nugen AI inference service temporarily unavailable."},
    },
)
async def ai_chat(
    payload: AIChatRequest,
    stream: Optional[bool] = Query(None, description="Override stream mode via query parameter"),
    _: Any = Depends(require_permission(PERM_CHATBOT_ASK)),
):
    """Chat with CLIMAFORGE AI conversational assistant."""
    should_stream = stream if stream is not None else payload.stream
    history_dicts = [{"role": m.role, "content": m.content} for m in payload.history]

    if should_stream:
        event_gen = nugen_ai_service.stream_chat(
            question=payload.message,
            scenario_id=payload.scenario_id,
            history=history_dicts,
        )
        return StreamingResponse(
            event_gen,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming response
    try:
        completion = await nugen_ai_service.generate_chat_completion(
            question=payload.message,
            scenario_id=payload.scenario_id,
            history=history_dicts,
        )
        return AIChatResponse(
            answer=completion["answer"],
            source=completion.get("source", "LLM"),
            model=completion.get("model", "Qwen/Qwen2.5-0.5B-Instruct"),
            provider="Nugen AI",
            scenario_id=payload.scenario_id or "",
            context_available=completion.get("context_available", True),
            is_advisory=True,
        )
    except NugenAIError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error occurred while generating AI response.",
        ) from exc

