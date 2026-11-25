from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, get_utc_now
from app.schemas.task import ErrorResponse, TodayResponse
from app.services import task_service

router = APIRouter(prefix="/api/today", tags=["today"])


@router.get("", response_model=TodayResponse, responses={404: {"model": ErrorResponse}})
def get_today_endpoint(
    care_recipient_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> TodayResponse:
    return task_service.get_today_tasks(
        db=db,
        care_recipient_id=care_recipient_id,
        now_utc=now_utc,
    )
