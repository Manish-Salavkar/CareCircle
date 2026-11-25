from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import CareRecipient, CareTask, FamilyMember, TaskStatus, TaskType


def seed_development_data(db: Session, tz_name: str = "UTC") -> dict[str, int]:
    created = {"care_recipients": 0, "family_members": 0, "care_tasks": 0}
    now_local = datetime.now(ZoneInfo(tz_name))

    care_recipient = db.scalar(select(CareRecipient).where(CareRecipient.name == "Mum"))
    if care_recipient is None:
        care_recipient = CareRecipient(name="Mum", date_of_birth=date(1952, 6, 15))
        db.add(care_recipient)
        db.flush()
        created["care_recipients"] += 1

    existing_members = {
        m.name: m
        for m in db.scalars(
            select(FamilyMember).where(FamilyMember.care_recipient_id == care_recipient.id)
        )
    }

    for name, relationship in [("Ravi", "Son"), ("Priya", "Daughter"), ("Amit", "Son")]:
        if name not in existing_members:
            member = FamilyMember(
                care_recipient_id=care_recipient.id,
                name=name,
                relationship=relationship,
            )
            db.add(member)
            db.flush()
            existing_members[name] = member
            created["family_members"] += 1

    existing_titles = set(
        db.scalars(select(CareTask.title).where(CareTask.care_recipient_id == care_recipient.id))
    )

    yesterday_local = (now_local - timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    two_days_ago_local = (now_local - timedelta(days=2)).replace(hour=15, minute=0, second=0, microsecond=0)
    in_two_days_local = (now_local + timedelta(days=2)).replace(hour=10, minute=30, second=0, microsecond=0)

    task_specs = [
        {
            "title": "Morning blood pressure medication",
            "description": "Amlodipine 5mg after breakfast with a full glass of water.",
            "task_type": TaskType.MEDICINE,
            "due_at": (now_local - timedelta(hours=8)).astimezone(timezone.utc),
            "status": TaskStatus.DONE,
            "completed_by_id": existing_members["Priya"].id,
            "completed_at": (now_local - timedelta(hours=7, minutes=45)).astimezone(timezone.utc),
        },
        {
            "title": "Afternoon vitamin D & calcium dose",
            "description": "Take 1 tablet after lunch.",
            "task_type": TaskType.MEDICINE,
            "due_at": (now_local - timedelta(hours=3)).astimezone(timezone.utc),
            "status": TaskStatus.PENDING,
            "completed_by_id": None,
            "completed_at": None,
        },
        {
            "title": "Evening diabetes medication",
            "description": "Metformin 500mg before dinner.",
            "task_type": TaskType.MEDICINE,
            "due_at": (now_local + timedelta(hours=3)).astimezone(timezone.utc),
            "status": TaskStatus.PENDING,
            "completed_by_id": None,
            "completed_at": None,
        },
        {
            "title": "Cardiology follow-up appointment",
            "description": "Bring updated blood pressure log and recent lab report for Dr. Mehta.",
            "task_type": TaskType.APPOINTMENT,
            "due_at": in_two_days_local.astimezone(timezone.utc),
            "status": TaskStatus.PENDING,
            "completed_by_id": None,
            "completed_at": None,
        },
        {
            "title": "Physiotherapy clinic visit",
            "description": "Weekly knee mobility session.",
            "task_type": TaskType.APPOINTMENT,
            "due_at": two_days_ago_local.astimezone(timezone.utc),
            "status": TaskStatus.DONE,
            "completed_by_id": existing_members["Amit"].id,
            "completed_at": (two_days_ago_local + timedelta(hours=1)).astimezone(timezone.utc),
        },
        {
            "title": "Morning check-in call",
            "description": "Quick call to check sleep quality and morning energy.",
            "task_type": TaskType.CHECK_IN,
            "due_at": yesterday_local.astimezone(timezone.utc),
            "status": TaskStatus.DONE,
            "completed_by_id": existing_members["Ravi"].id,
            "completed_at": (yesterday_local + timedelta(minutes=10)).astimezone(timezone.utc),
        },
        {
            "title": "Evening check-in call",
            "description": "Confirm dinner, hydration, and evening comfort.",
            "task_type": TaskType.CHECK_IN,
            "due_at": (now_local + timedelta(hours=5)).astimezone(timezone.utc),
            "status": TaskStatus.PENDING,
            "completed_by_id": None,
            "completed_at": None,
        },
    ]

    for spec in task_specs:
        if spec["title"] not in existing_titles:
            db.add(CareTask(care_recipient_id=care_recipient.id, **spec))
            created["care_tasks"] += 1

    db.commit()
    return created


def main() -> None:
    settings = get_settings()
    if settings.app_env.lower() == "production":
        raise RuntimeError("Refusing to run development seed script in production.")

    with SessionLocal() as db:
        created = seed_development_data(db, tz_name=settings.app_timezone)
        print(
            "Seed complete: "
            f"{created['care_recipients']} care recipient(s), "
            f"{created['family_members']} family member(s), "
            f"{created['care_tasks']} care task(s) created."
        )


if __name__ == "__main__":
    main()
