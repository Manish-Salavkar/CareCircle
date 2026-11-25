import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.core.database import Base, get_db
from app.models import (
    AIInteractionLog,
    CareRecipient,
    CareTask,
    FamilyMember,
    TaskStatus,
    TaskType,
)


def test_expected_tables_registered_on_metadata() -> None:
    assert set(Base.metadata.tables.keys()) == {
        "care_recipients",
        "family_members",
        "care_tasks",
        "ai_interaction_logs",
    }


def test_care_tasks_foreign_keys_and_indexes() -> None:
    care_tasks = Base.metadata.tables["care_tasks"]

    fk_targets = {
        fk.column.table.name: (fk.parent.name, fk.ondelete)
        for fk in care_tasks.foreign_keys
    }
    assert fk_targets["care_recipients"] == ("care_recipient_id", "CASCADE")
    assert fk_targets["family_members"] == ("completed_by_id", "SET NULL")

    indexed_column_sets = {
        tuple(col.name for col in idx.columns) for idx in care_tasks.indexes
    }
    assert ("care_recipient_id",) in indexed_column_sets
    assert ("due_at",) in indexed_column_sets
    assert ("status",) in indexed_column_sets
    assert ("care_recipient_id", "status", "due_at") in indexed_column_sets


def test_task_status_excludes_overdue() -> None:
    allowed_statuses = {status.value for status in TaskStatus}
    assert allowed_statuses == {"pending", "done"}
    assert "overdue" not in allowed_statuses


def test_care_task_is_overdue_dynamic_calculation() -> None:
    now_utc = datetime.now(timezone.utc)
    recipient_id = uuid.uuid4()

    overdue_task = CareTask(
        care_recipient_id=recipient_id,
        title="Overdue medicine",
        task_type=TaskType.MEDICINE,
        due_at=now_utc - timedelta(hours=1),
        status=TaskStatus.PENDING,
    )
    upcoming_task = CareTask(
        care_recipient_id=recipient_id,
        title="Upcoming check-in",
        task_type=TaskType.CHECK_IN,
        due_at=now_utc + timedelta(hours=2),
        status=TaskStatus.PENDING,
    )
    completed_past_task = CareTask(
        care_recipient_id=recipient_id,
        title="Completed appointment",
        task_type=TaskType.APPOINTMENT,
        due_at=now_utc - timedelta(days=1),
        status=TaskStatus.DONE,
        completed_at=now_utc - timedelta(days=1),
    )

    assert overdue_task.is_overdue is True
    assert upcoming_task.is_overdue is False
    assert completed_past_task.is_overdue is False


def test_ai_interaction_log_model_instantiation() -> None:
    log = AIInteractionLog(
        question="Did Mum take her morning medicine?",
        context_sent={"care_recipient": "Mum", "tasks_count": 3},
        answer="Yes, Priya marked Morning blood pressure medication as done.",
        latency_ms=420,
    )
    assert log.context_sent["care_recipient"] == "Mum"
    assert log.latency_ms == 420


def test_care_recipient_and_family_member_models() -> None:
    recipient = CareRecipient(name="Mum")
    member = FamilyMember(
        care_recipient=recipient,
        name="Priya",
        relationship="Daughter",
    )
    assert member.care_recipient is recipient
    assert member in recipient.family_members


def test_get_db_yields_and_closes_session(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = False

    class DummySession:
        def close(self) -> None:
            nonlocal closed
            closed = True

    monkeypatch.setattr("app.core.database.SessionLocal", lambda: DummySession())

    gen = get_db()
    session = next(gen)
    assert isinstance(session, DummySession)
    with pytest.raises(StopIteration):
        next(gen)
    assert closed is True
