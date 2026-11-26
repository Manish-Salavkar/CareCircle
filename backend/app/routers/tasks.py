from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.care_task import TaskStatus, TaskType
from app.schemas.task import TaskCompleteRequest, TaskCreate, TaskResponse, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("", response_model=list[TaskResponse])
def list_tasks_endpoint(
    status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    care_recipient_id: UUID | None = None,
    db: Session = Depends(get_db)
):
    return task_service.list_tasks(
        db=db,
        status=status,
        task_type=task_type,
        care_recipient_id=care_recipient_id
    )

@router.post("", response_model=TaskResponse, status_code=201)
def create_task_endpoint(
    payload: TaskCreate,
    db: Session = Depends(get_db)
):
    return task_service.create_task(db=db, payload=payload)

@router.get("/{task_id}", response_model=TaskResponse)
def get_task_endpoint(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    return task_service.get_task(db=db, task_id=task_id)

@router.patch("/{task_id}", response_model=TaskResponse)
def update_task_endpoint(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db)
):
    return task_service.update_task(db=db, task_id=task_id, payload=payload)

@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task_endpoint(
    task_id: UUID,
    payload: TaskCompleteRequest,
    db: Session = Depends(get_db)
):
    return task_service.complete_task(
        db=db,
        task_id=task_id,
        completed_by_id=payload.completed_by_id
    )