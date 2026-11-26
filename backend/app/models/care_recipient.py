import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CareRecipient(Base):
    __tablename__ = "care_recipients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    family_members: Mapped[list["FamilyMember"]] = relationship(
        back_populates="care_recipient", cascade="all, delete-orphan"
    )
    care_tasks: Mapped[list["CareTask"]] = relationship(
        back_populates="care_recipient", cascade="all, delete-orphan"
    )