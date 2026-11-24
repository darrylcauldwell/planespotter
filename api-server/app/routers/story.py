import logging
from collections.abc import AsyncIterator
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.aircraft import AircraftService
from app.services.llm import LLMError, LLMNotConfigured
from app.services.story import tell_story

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/aircraft", tags=["ai"])


@router.get("/{icao24}/story", response_class=StreamingResponse)
async def aircraft_story(icao24: str, db: AsyncSession = Depends(get_db)):
    """Stream a short plain-English description of an aircraft as the model writes it."""
    aircraft = await AircraftService(db).get_by_icao24(icao24)
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found")

    pieces = tell_story(aircraft)
    # Wait for the first words before answering, so a model that is missing or failing gets a
    # proper status code rather than a 200 that ends with nothing.
    try:
        first = await anext(pieces, "")
    except LLMNotConfigured:
        raise HTTPException(status_code=503, detail="No language model is configured")
    except LLMError as e:
        logger.error(f"Story failed: {e}")
        raise HTTPException(status_code=502, detail="The language model did not answer")

    async def story() -> AsyncIterator[str]:
        yield first
        try:
            async for piece in pieces:
                yield piece
        except LLMError as e:
            logger.error(f"Story stopped part way: {e}")
            yield "\n\n(The language model stopped before it finished.)"

    return StreamingResponse(story(), media_type="text/plain; charset=utf-8")
