from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.assistant import AssistantAskRequest
from app.services import assistant_service, task_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

@router.post("/ask")
async def ask_assistant_endpoint(
    payload: AssistantAskRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    recipient = task_service.resolve_care_recipient(db, payload.care_recipient_id)

    return StreamingResponse(
        assistant_service.stream_assistant_response(
            request=request,
            db=db,
            question=payload.question,
            care_recipient_id=recipient.id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )