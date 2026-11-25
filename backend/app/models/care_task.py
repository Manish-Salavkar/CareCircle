import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.care_recipient import CareRecipient
    from app.models.family_member import FamilyMember


class TaskType(str, Enum):
    MEDICINE = "medicine"
    APPOINTMENT = "appointment"
    CHECK_IN = "check_in"


class TaskStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"


class CareTask(Base):
    __tablename__ = "care_tasks"
    __table_args__ = (
        Index("ix_care_tasks_recipient_status_due", "care_recipient_id", "status", "due_at"),
        CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL AND completed_by_id IS NULL) "
            "OR (status = 'done' AND completed_at IS NOT NULL)",
            name="completion_consistency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    care_recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_recipients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(
        SAEnum(
            TaskType,
            name="task_type_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            length=32,
            create_constraint=True,
        ),
        nullable=False,
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SAEnum(
            TaskStatus,
            name="task_status_enum",
            native_enum=False,
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            length=16,
            create_constraint=True,
        ),
        nullable=False,
        default=TaskStatus.PENDING,
        server_default=text("'pending'"),
        index=True,
    )
    # Keep task history if a family member is removed
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("family_members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    care_recipient: Mapped["CareRecipient"] = relationship(
        "CareRecipient",
        back_populates="care_tasks",
    )
    completed_by: Mapped["FamilyMember | None"] = relationship(
        "FamilyMember",
        back_populates="completed_tasks",
    )

    @property
    def is_overdue(self) -> bool:
        if self.status != TaskStatus.PENDING:
            return False
        now_utc = datetime.now(timezone.utc)
        due_utc = (
            self.due_at.astimezone(timezone.utc)
            if self.due_at.tzinfo is not None
            else self.due_at.replace(tzinfo=timezone.utc)
        )
        return due_utc < now_utc
