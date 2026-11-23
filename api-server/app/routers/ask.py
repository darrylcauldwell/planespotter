import logging
from fastapi import APIRouter, HTTPException
from app.schemas.ask import AskRequest, AskResponse
from app.services.ask import interpret_question
from app.services.llm import LLMError, LLMNotConfigured

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask", tags=["ai"])


@router.post("", response_model=AskResponse)
async def ask(request: AskRequest):
    """Turn a plain-English question into filters for the aircraft search."""
    try:
        answer = await interpret_question(request.question)
    except LLMNotConfigured:
        raise HTTPException(status_code=503, detail="No language model is configured")
    except LLMError as e:
        logger.error(f"Ask failed: {e}")
        raise HTTPException(status_code=502, detail="The language model did not answer")

    return AskResponse(
        question=request.question,
        filters=answer.output,
        model=answer.model,
        elapsed_ms=round(answer.seconds * 1000),
    )
