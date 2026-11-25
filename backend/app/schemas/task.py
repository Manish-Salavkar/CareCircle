from datetime import date, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.care_task import CareTask, TaskStatus, TaskType


def _to_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information.")
    return value.astimezone(timezone.utc)


def _clean_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be blank.")
    return cleaned


class ErrorResponse(BaseModel):
    detail: str


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    care_recipient_id: UUID
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskType
    due_at: datetime

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _clean_text(value, "title")

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime) -> datetime:
        return _to_utc(value, "due_at")


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    task_type: TaskType | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("title cannot be null.")
        return _clean_text(value, "title")

    @field_validator("task_type")
    @classmethod
    def validate_task_type(cls, value: TaskType | None) -> TaskType:
        if value is None:
            raise ValueError("task_type cannot be null.")
        return value

    @field_validator("due_at")
    @classmethod
    def validate_due_at(cls, value: datetime | None) -> datetime:
        if value is None:
            raise ValueError("due_at cannot be null.")
        return _to_utc(value, "due_at")


class TaskCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    completed_by_name: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_task(cls, task: CareTask, now_utc: datetime | None = None) -> "TaskResponse":
        now = now_utc or datetime.now(timezone.utc)
        due_utc = (
            task.due_at.astimezone(timezone.utc)
            if task.due_at.tzinfo is not None
            else task.due_at.replace(tzinfo=timezone.utc)
        )
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
            completed_by_name=task.completed_by.name if task.completed_by else None,
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
