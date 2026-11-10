"""Read-only grounded chatbot API."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.chatbot import generate_answer
from app.dependencies.auth import require_permission
from app.security.rbac import PERM_CHATBOT_ASK


router = APIRouter(prefix="/chatbot", tags=["Grounded Chatbot"])


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=2000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be blank")
        return value.strip()


class ChatbotRequest(BaseModel):
    scenario_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=12)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be blank")
        return value.strip()


class ChatbotResponse(BaseModel):
    answer: str
    source: Literal["LLM", "DETERMINISTIC_FALLBACK"]
    mode: Literal["grounded_llm", "deterministic_fallback"]
    scenario_id: str
    context_available: bool


@router.post("/message", response_model=ChatbotResponse, summary="Ask the grounded CLIMAFORGE assistant")
async def chatbot_message(
    payload: ChatbotRequest,
    _: Any = Depends(require_permission(PERM_CHATBOT_ASK)),
) -> ChatbotResponse:
    result = generate_answer(
        scenario_id=payload.scenario_id,
        question=payload.question,
        history=[item.model_dump() for item in payload.history],
    )
    return ChatbotResponse(**result)
