from datetime import date, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.care_task import CareTask, TaskStatus, TaskType

class ErrorResponse(BaseModel):
    detail: str


class TaskCreate(BaseModel):
    care_recipient_id: UUID
    title: str
    description: str | None = None
    task_type: TaskType
    due_at: datetime


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    task_type: TaskType | None = None
    due_at: datetime | None = None


class TaskCompleteRequest(BaseModel):
    completed_by_id: UUID


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_recipient_id: UUID
    title: str
    description: str | None
    task_type: TaskType
    due_at: datetime
    status: TaskStatus
    is_overdue: bool
    completed_by_id: UUID | None
    completed_by_name: str | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: CareTask) -> "TaskResponse":
        now = datetime.now(timezone.utc)
        due_utc = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
        
        return cls(
            id=task.id,
            care_recipient_id=task.care_recipient_id,
            title=task.title,
            description=task.description,
            task_type=task.task_type,
            due_at=task.due_at,
            status=task.status,
            is_overdue=task.status == TaskStatus.PENDING and due_utc < now,
            completed_by_id=task.completed_by_id,
            completed_by_name=task.completed_by.name if getattr(task, "completed_by", None) else None,
            completed_at=task.completed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class FamilyMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    care_recipient_id: UUID
    name: str
    relationship: str


class TodayCounts(BaseModel):
    overdue: int
    due: int
    done: int


class TodayResponse(BaseModel):
    date: date
    care_recipient_id: UUID
    care_recipient_name: str
    overdue: list[TaskResponse]
    due: list[TaskResponse]
    done: list[TaskResponse]
    counts: TodayCounts