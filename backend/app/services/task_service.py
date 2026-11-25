from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.models import CareRecipient, CareTask, FamilyMember, TaskStatus, TaskType
from app.schemas.task import (
    FamilyMemberResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TodayCounts,
    TodayResponse,
)


def resolve_care_recipient(
    db: Session,
    care_recipient_id: UUID | None = None,
) -> CareRecipient:
    if care_recipient_id is not None:
        recipient = db.get(CareRecipient, care_recipient_id)
        if recipient is None:
            raise HTTPException(status_code=404, detail="Care recipient not found.")
        return recipient

    recipient = db.scalar(
        select(CareRecipient).order_by(CareRecipient.created_at.asc()).limit(1)
    )
    if recipient is None:
        raise HTTPException(status_code=404, detail="No care recipient found.")
    return recipient


def list_family_members(
    db: Session,
    care_recipient_id: UUID | None = None,
) -> list[FamilyMemberResponse]:
    recipient = resolve_care_recipient(db, care_recipient_id)
    members = db.scalars(
        select(FamilyMember)
        .where(FamilyMember.care_recipient_id == recipient.id)
        .order_by(FamilyMember.name.asc(), FamilyMember.created_at.asc())
    ).all()
    return [FamilyMemberResponse.model_validate(m) for m in members]


def list_tasks(
    db: Session,
    status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
) -> list[TaskResponse]:
    stmt = (
        select(CareTask)
        .options(joinedload(CareTask.completed_by))
        .order_by(CareTask.due_at.asc(), CareTask.created_at.asc())
    )
    if care_recipient_id is not None:
        stmt = stmt.where(CareTask.care_recipient_id == care_recipient_id)
    if status is not None:
        stmt = stmt.where(CareTask.status == status)
    if task_type is not None:
        stmt = stmt.where(CareTask.task_type == task_type)

    tasks = db.scalars(stmt).all()
    return [TaskResponse.from_task(t, now_utc=now_utc) for t in tasks]


def create_task(
    db: Session,
    payload: TaskCreate,
    now_utc: datetime | None = None,
) -> TaskResponse:
    if db.get(CareRecipient, payload.care_recipient_id) is None:
        raise HTTPException(status_code=404, detail="Care recipient not found.")

    task = CareTask(
        care_recipient_id=payload.care_recipient_id,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        due_at=payload.due_at.astimezone(timezone.utc),
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.from_task(task, now_utc=now_utc)


def _find_task(db: Session, task_id: UUID) -> CareTask:
    task = db.scalar(
        select(CareTask)
        .options(joinedload(CareTask.completed_by))
        .where(CareTask.id == task_id)
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Care task not found.")
    return task


def get_task(
    db: Session,
    task_id: UUID,
    now_utc: datetime | None = None,
) -> TaskResponse:
    return TaskResponse.from_task(_find_task(db, task_id), now_utc=now_utc)


def update_task(
    db: Session,
    task_id: UUID,
    payload: TaskUpdate,
    now_utc: datetime | None = None,
) -> TaskResponse:
    task = _find_task(db, task_id)
    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        if field == "due_at" and value is not None:
            value = value.astimezone(timezone.utc)
        setattr(task, field, value)

    if updates:
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)

    return TaskResponse.from_task(task, now_utc=now_utc)


def complete_task(
    db: Session,
    task_id: UUID,
    completed_by_id: UUID,
    now_utc: datetime | None = None,
) -> TaskResponse:
    task = db.get(CareTask, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Care task not found.")

    member = db.get(FamilyMember, completed_by_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Family member not found.")

    if member.care_recipient_id != task.care_recipient_id:
        raise HTTPException(
            status_code=400,
            detail="Family member does not belong to the care recipient for this task.",
        )

    if task.status == TaskStatus.DONE:
        raise HTTPException(status_code=409, detail="Care task is already completed.")

    # Conditional update prevents two concurrent requests from overwriting completion audit data
    completion_time = now_utc or datetime.now(timezone.utc)
    stmt = (
        update(CareTask)
        .where(CareTask.id == task_id, CareTask.status == TaskStatus.PENDING)
        .values(
            status=TaskStatus.DONE,
            completed_by_id=member.id,
            completed_at=completion_time,
            updated_at=completion_time,
        )
        .returning(CareTask.id)
    )
    if db.execute(stmt).scalar_one_or_none() is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="Care task is already completed.")

    db.commit()
    db.expire_all()
    return TaskResponse.from_task(_find_task(db, task_id), now_utc=completion_time)


def get_today_tasks(
    db: Session,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
    tz_name: str | None = None,
) -> TodayResponse:
    recipient = resolve_care_recipient(db, care_recipient_id)

    local_tz = ZoneInfo(tz_name or get_settings().app_timezone)
    reference_utc = now_utc or datetime.now(timezone.utc)
    today_date = reference_utc.astimezone(local_tz).date()

    # Convert local start/end of day to UTC for database filtering
    today_start_utc = datetime.combine(today_date, time.min, tzinfo=local_tz).astimezone(timezone.utc)
    tomorrow_start_utc = datetime.combine(today_date + timedelta(days=1), time.min, tzinfo=local_tz).astimezone(timezone.utc)

    overdue_tasks = db.scalars(
        select(CareTask)
        .options(joinedload(CareTask.completed_by))
        .where(
            CareTask.care_recipient_id == recipient.id,
            CareTask.status == TaskStatus.PENDING,
            CareTask.due_at < reference_utc,
        )
        .order_by(CareTask.due_at.asc(), CareTask.created_at.asc())
    ).all()

    due_tasks = db.scalars(
        select(CareTask)
        .options(joinedload(CareTask.completed_by))
        .where(
            CareTask.care_recipient_id == recipient.id,
            CareTask.status == TaskStatus.PENDING,
            CareTask.due_at >= reference_utc,
            CareTask.due_at < tomorrow_start_utc,
        )
        .order_by(CareTask.due_at.asc(), CareTask.created_at.asc())
    ).all()

    done_tasks = db.scalars(
        select(CareTask)
        .options(joinedload(CareTask.completed_by))
        .where(
            CareTask.care_recipient_id == recipient.id,
            CareTask.status == TaskStatus.DONE,
            CareTask.completed_at >= today_start_utc,
            CareTask.completed_at < tomorrow_start_utc,
        )
        .order_by(CareTask.completed_at.desc(), CareTask.created_at.asc())
    ).all()

    overdue_items = [TaskResponse.from_task(t, now_utc=reference_utc) for t in overdue_tasks]
    due_items = [TaskResponse.from_task(t, now_utc=reference_utc) for t in due_tasks]
    done_items = [TaskResponse.from_task(t, now_utc=reference_utc) for t in done_tasks]

    return TodayResponse(
        date=today_date,
        care_recipient_id=recipient.id,
        care_recipient_name=recipient.name,
        overdue=overdue_items,
        due=due_items,
        done=done_items,
        counts=TodayCounts(
            overdue=len(overdue_items),
            due=len(due_items),
            done=len(done_items),
        ),
    )
