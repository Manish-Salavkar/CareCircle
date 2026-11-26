import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskType(str, Enum):
    MEDICINE = "medicine"
    APPOINTMENT = "appointment"
    CHECK_IN = "check_in"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"


class CareTask(Base):
    __tablename__ = "care_tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    care_recipient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("care_recipients.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    care_recipient: Mapped["CareRecipient"] = relationship(back_populates="care_tasks")
    completed_by: Mapped["FamilyMember"] = relationship(back_populates="completed_tasks")

    @property
    def is_overdue(self) -> bool:
        if self.status != TaskStatus.PENDING:
            return False
        return self.due_at < datetime.now(timezone.utc)