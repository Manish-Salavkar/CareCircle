from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db, get_utc_now
from app.schemas.assistant import AssistantAskRequest
from app.schemas.task import ErrorResponse
from app.services import assistant_service, task_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post(
    "/ask",
    responses={
        200: {"content": {"text/event-stream": {}}},
        404: {"model": ErrorResponse},
        422: {"description": "Validation error"},
    },
)
async def ask_assistant_endpoint(
    payload: AssistantAskRequest,
    request: Request,
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> StreamingResponse:
    recipient = task_service.resolve_care_recipient(db, payload.care_recipient_id)

    return StreamingResponse(
        assistant_service.stream_assistant_response(
            request=request,
            db=db,
            question=payload.question,
            care_recipient_id=recipient.id,
            now_utc=now_utc,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
