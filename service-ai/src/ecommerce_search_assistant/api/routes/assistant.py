from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ecommerce_search_assistant.schemas.assistant import AssistantChatResponse
from ecommerce_search_assistant.schemas.chat import ChatRequest
from ecommerce_search_assistant.services.assistant.factory import get_assistant_workflow
from ecommerce_search_assistant.services.assistant.workflow import AssistantWorkflow, TurnSequenceConflict

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse, response_model_exclude_none=True)
def assistant_chat(
    request: ChatRequest,
    assistant: Annotated[AssistantWorkflow, Depends(get_assistant_workflow)],
) -> AssistantChatResponse:
    try:
        return assistant.chat(request)
    except TurnSequenceConflict as error:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "turn_sequence_conflict",
                "expected": error.expected,
                "received": error.received,
            },
        ) from error
