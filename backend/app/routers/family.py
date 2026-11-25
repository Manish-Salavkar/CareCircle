from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.task import ErrorResponse, FamilyMemberResponse
from app.services import task_service

router = APIRouter(prefix="/api/family-members", tags=["family-members"])


@router.get("", response_model=list[FamilyMemberResponse], responses={404: {"model": ErrorResponse}})
def list_family_members_endpoint(
    care_recipient_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[FamilyMemberResponse]:
    return task_service.list_family_members(db=db, care_recipient_id=care_recipient_id)
