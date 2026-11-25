from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_utc_now
from app.models.care_task import TaskStatus, TaskType
from app.schemas.task import (
    ErrorResponse,
    TaskCompleteRequest,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks_endpoint(
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    task_type: TaskType | None = Query(default=None),
    care_recipient_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> list[TaskResponse]:
    return task_service.list_tasks(
        db=db,
        status=task_status,
        task_type=task_type,
        care_recipient_id=care_recipient_id,
        now_utc=now_utc,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
def create_task_endpoint(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> TaskResponse:
    return task_service.create_task(db=db, payload=payload, now_utc=now_utc)


@router.get("/{task_id}", response_model=TaskResponse, responses={404: {"model": ErrorResponse}})
def get_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> TaskResponse:
    return task_service.get_task(db=db, task_id=task_id, now_utc=now_utc)


@router.patch("/{task_id}", response_model=TaskResponse, responses={404: {"model": ErrorResponse}})
def update_task_endpoint(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> TaskResponse:
    return task_service.update_task(db=db, task_id=task_id, payload=payload, now_utc=now_utc)


@router.post(
    "/{task_id}/complete",
    response_model=TaskResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
def complete_task_endpoint(
    task_id: UUID,
    payload: TaskCompleteRequest,
    db: Session = Depends(get_db),
    now_utc: datetime = Depends(get_utc_now),
) -> TaskResponse:
    return task_service.complete_task(
        db=db,
        task_id=task_id,
        completed_by_id=payload.completed_by_id,
        now_utc=now_utc,
    )
