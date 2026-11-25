import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.care_task import CareTask
    from app.models.family_member import FamilyMember


class CareRecipient(Base):
    __tablename__ = "care_recipients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    family_members: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember",
        back_populates="care_recipient",
        cascade="all, delete-orphan",
    )
    care_tasks: Mapped[list["CareTask"]] = relationship(
        "CareTask",
        back_populates="care_recipient",
        cascade="all, delete-orphan",
    )
