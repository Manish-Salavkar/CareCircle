from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CareRecipient, CareTask, FamilyMember, TaskStatus, TaskType
from app.schemas.task import (
    FamilyMemberResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TodayCounts,
    TodayResponse,
)

def resolve_care_recipient(db: Session, care_recipient_id: UUID | None = None) -> CareRecipient:
    if care_recipient_id:
        recipient = db.get(CareRecipient, care_recipient_id)
        if not recipient:
            raise HTTPException(status_code=404, detail="Care recipient not found.")
        return recipient

    recipient = db.scalar(select(CareRecipient).limit(1))
    if not recipient:
        raise HTTPException(status_code=404, detail="No care recipient found.")
    return recipient

def list_family_members(db: Session, care_recipient_id: UUID | None = None) -> list[FamilyMemberResponse]:
    recipient = resolve_care_recipient(db, care_recipient_id)
    members = db.scalars(
        select(FamilyMember)
        .where(FamilyMember.care_recipient_id == recipient.id)
    ).all()
    return [FamilyMemberResponse.model_validate(m) for m in members]

def list_tasks(
    db: Session,
    status: TaskStatus | None = None,
    task_type: TaskType | None = None,
    care_recipient_id: UUID | None = None,
) -> list[TaskResponse]:
    stmt = select(CareTask)
    
    if care_recipient_id:
        stmt = stmt.where(CareTask.care_recipient_id == care_recipient_id)
    if status:
        stmt = stmt.where(CareTask.status == status)
    if task_type:
        stmt = stmt.where(CareTask.task_type == task_type)

    tasks = db.scalars(stmt).all()
    return [TaskResponse.from_task(t) for t in tasks]

def create_task(db: Session, payload: TaskCreate) -> TaskResponse:
    if not db.get(CareRecipient, payload.care_recipient_id):
        raise HTTPException(status_code=404, detail="Care recipient not found.")

    task = CareTask(
        care_recipient_id=payload.care_recipient_id,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        due_at=payload.due_at,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return TaskResponse.from_task(task)

def get_task(db: Session, task_id: UUID) -> TaskResponse:
    task = db.get(CareTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Care task not found.")
    return TaskResponse.from_task(task)

def update_task(db: Session, task_id: UUID, payload: TaskUpdate) -> TaskResponse:
    task = db.get(CareTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Care task not found.")
    
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)

    if updates:
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)

    return TaskResponse.from_task(task)

def complete_task(db: Session, task_id: UUID, completed_by_id: UUID) -> TaskResponse:
    task = db.get(CareTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Care task not found.")

    member = db.get(FamilyMember, completed_by_id)
    if not member:
        raise HTTPException(status_code=404, detail="Family member not found.")

    if member.care_recipient_id != task.care_recipient_id:
        raise HTTPException(status_code=400, detail="Invalid family member.")

    if task.status == TaskStatus.DONE:
        raise HTTPException(status_code=400, detail="Task already completed.")

    task.status = TaskStatus.DONE
    task.completed_by_id = member.id
    task.completed_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(task)
    return TaskResponse.from_task(task)

def get_today_tasks(
    db: Session,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
    tz_name: str | None = None,
) -> TodayResponse:
    recipient = resolve_care_recipient(db, care_recipient_id)
    
    tz = tz_name or settings.app_timezone
    local_tz = ZoneInfo(tz)
    current_utc = now_utc or datetime.now(timezone.utc)
    today_date = current_utc.astimezone(local_tz).date()

    today_start_utc = datetime.combine(today_date, time.min, tzinfo=local_tz).astimezone(timezone.utc)
    tomorrow_start_utc = datetime.combine(today_date + timedelta(days=1), time.min, tzinfo=local_tz).astimezone(timezone.utc)

    all_tasks = db.scalars(
        select(CareTask)
        .where(CareTask.care_recipient_id == recipient.id)
    ).all()
    
    overdue_tasks = []
    due_tasks = []
    done_tasks = []
    
    for task in all_tasks:
        if task.status == TaskStatus.PENDING:
            if task.due_at < current_utc:
                overdue_tasks.append(task)
            elif task.due_at >= current_utc and task.due_at < tomorrow_start_utc:
                due_tasks.append(task)
        elif task.status == TaskStatus.DONE and task.completed_at:
            if task.completed_at >= today_start_utc and task.completed_at < tomorrow_start_utc:
                done_tasks.append(task)

    overdue_tasks.sort(key=lambda t: t.due_at)
    due_tasks.sort(key=lambda t: t.due_at)
    done_tasks.sort(key=lambda t: t.completed_at, reverse=True)

    return TodayResponse(
        date=today_date,
        care_recipient_id=recipient.id,
        care_recipient_name=recipient.name,
        overdue=[TaskResponse.from_task(t) for t in overdue_tasks],
        due=[TaskResponse.from_task(t) for t in due_tasks],
        done=[TaskResponse.from_task(t) for t in done_tasks],
        counts=TodayCounts(
            overdue=len(overdue_tasks),
            due=len(due_tasks),
            done=len(done_tasks),
        ),
    )