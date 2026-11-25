"""Tests for Phase 4 streaming Ask About Today assistant and interaction logging."""

import json
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import engine, get_db, get_utc_now
from app.main import app
from app.models import (
    AIInteractionLog,
    CareRecipient,
    CareTask,
    FamilyMember,
    TaskStatus,
    TaskType,
)
from app.services import assistant_service

FIXED_NOW_UTC = datetime(2026, 11, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def db_session() -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_utc_now] = lambda: FIXED_NOW_UTC

    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def assistant_context(db_session: Session) -> dict[str, object]:
    """Seed isolated deterministic Today tasks for assistant tests."""
    recipient = CareRecipient(name="Mum", date_of_birth=date(1952, 6, 15))
    db_session.add(recipient)
    db_session.flush()

    priya = FamilyMember(
        care_recipient_id=recipient.id,
        name="Priya",
        relationship="Daughter",
    )
    ravi = FamilyMember(
        care_recipient_id=recipient.id,
        name="Ravi",
        relationship="Son",
    )
    db_session.add_all([priya, ravi])
    db_session.flush()

    overdue_med = CareTask(
        care_recipient_id=recipient.id,
        title="Afternoon vitamin D dose",
        task_type=TaskType.MEDICINE,
        due_at=FIXED_NOW_UTC - timedelta(hours=2),
        status=TaskStatus.PENDING,
    )
    due_med = CareTask(
        care_recipient_id=recipient.id,
        title="Evening diabetes medicine",
        task_type=TaskType.MEDICINE,
        due_at=FIXED_NOW_UTC + timedelta(hours=4),
        status=TaskStatus.PENDING,
    )
    due_checkin = CareTask(
        care_recipient_id=recipient.id,
        title="Evening check-in call",
        task_type=TaskType.CHECK_IN,
        due_at=FIXED_NOW_UTC + timedelta(hours=5),
        status=TaskStatus.PENDING,
    )
    done_appt = CareTask(
        care_recipient_id=recipient.id,
        title="Physiotherapy appointment",
        task_type=TaskType.APPOINTMENT,
        due_at=FIXED_NOW_UTC - timedelta(hours=4),
        status=TaskStatus.DONE,
        completed_by_id=priya.id,
        completed_at=FIXED_NOW_UTC - timedelta(hours=3),
    )
    db_session.add_all([overdue_med, due_med, due_checkin, done_appt])
    db_session.commit()

    return {"recipient": recipient, "priya": priya, "ravi": ravi}


def _parse_sse_stream(raw_text: str) -> list[tuple[str, dict[str, object]]]:
    """Parse raw SSE text into a list of (event_name, json_payload) tuples."""
    events: list[tuple[str, dict[str, object]]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = "message"
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())
        if data_lines:
            events.append((event_name, json.loads("\n".join(data_lines))))
    return events


def test_assistant_streams_sse_from_today_context_and_logs_interaction(
    client: TestClient,
    db_session: Session,
    assistant_context: dict[str, object],
) -> None:
    """Assistant streams progressive token events, finishes with done, and persists AIInteractionLog."""
    recipient: CareRecipient = assistant_context["recipient"]  # type: ignore[assignment]
    question = "What medicines are due today?"
    existing_ids = set(db_session.scalars(select(AIInteractionLog.id)).all())

    with client.stream(
        "POST",
        "/api/assistant/ask",
        json={"question": question, "care_recipient_id": str(recipient.id)},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = "".join(response.iter_text())

    events = _parse_sse_stream(body)
    token_events = [payload for name, payload in events if name == "token"]
    done_events = [payload for name, payload in events if name == "done"]

    assert len(token_events) > 1
    assert len(done_events) == 1
    assert events[-1][0] == "done"

    full_answer = "".join(str(item["chunk"]) for item in token_events)
    assert "Afternoon vitamin D dose" in full_answer
    assert "Evening diabetes medicine" in full_answer
    assert "Physiotherapy appointment" not in full_answer

    new_logs = [
        row
        for row in db_session.scalars(select(AIInteractionLog)).all()
        if row.id not in existing_ids
    ]
    assert len(new_logs) == 1
    log = new_logs[0]
    assert log.question == question
    assert log.answer == full_answer
    assert log.latency_ms >= 0
    assert log.created_at.tzinfo is not None
    assert log.context_sent["care_recipient_name"] == "Mum"
    assert log.context_sent["counts"] == {"overdue": 1, "due": 2, "done": 1}


def test_assistant_answers_overdue_completed_and_who_questions(
    client: TestClient,
    assistant_context: dict[str, object],
) -> None:
    """Verify overdue, appointment completion, and latest completer questions."""
    recipient: CareRecipient = assistant_context["recipient"]  # type: ignore[assignment]

    def ask(q: str) -> str:
        resp = client.post(
            "/api/assistant/ask",
            json={"question": q, "care_recipient_id": str(recipient.id)},
        )
        assert resp.status_code == 200
        events = _parse_sse_stream(resp.text)
        return "".join(str(p["chunk"]) for name, p in events if name == "token")

    overdue_ans = ask("What tasks are overdue?")
    assert "Afternoon vitamin D dose" in overdue_ans

    appt_ans = ask("Have all appointments been completed?")
    assert "Yes" in appt_ans
    assert "Physiotherapy appointment" in appt_ans
    assert "Priya" in appt_ans

    who_ans = ask("Who completed the last task?")
    assert "Physiotherapy appointment" in who_ans
    assert "Priya" in who_ans


def test_assistant_does_not_invent_absent_information_or_medical_advice(
    client: TestClient,
    assistant_context: dict[str, object],
) -> None:
    """Assistant refuses to invent missing tasks/people and avoids medical advice."""
    recipient: CareRecipient = assistant_context["recipient"]  # type: ignore[assignment]

    def ask(q: str) -> str:
        resp = client.post(
            "/api/assistant/ask",
            json={"question": q, "care_recipient_id": str(recipient.id)},
        )
        assert resp.status_code == 200
        events = _parse_sse_stream(resp.text)
        return "".join(str(p["chunk"]) for name, p in events if name == "token")

    absent_ans = ask("When is the dentist appointment?")
    assert "no appointments" not in absent_ans.lower() or "dentist" not in absent_ans.lower()
    # Notice "dentist" is not in schedule; if "appointment" triggers appointment summary,
    # it only mentions Physiotherapy appointment and never invents a dentist!
    assert "dentist" not in absent_ans.lower()

    unrelated_ans = ask("Did Mum eat breakfast?")
    assert "don't have information" in unrelated_ans.lower()
    assert "breakfast" not in unrelated_ans.lower()

    medical_ans = ask("Should I give a double dose of metformin?")
    assert "cannot provide medical advice" in medical_ans.lower()


def test_assistant_rejects_empty_questions_and_missing_recipient(
    client: TestClient,
    db_session: Session,
    assistant_context: dict[str, object],
) -> None:
    """Empty/blank questions return 422, missing recipient returns 404, and no log is created."""
    recipient: CareRecipient = assistant_context["recipient"]  # type: ignore[assignment]
    before_ids = set(db_session.scalars(select(AIInteractionLog.id)).all())

    assert (
        client.post(
            "/api/assistant/ask",
            json={"question": "", "care_recipient_id": str(recipient.id)},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/assistant/ask",
            json={"question": "   ", "care_recipient_id": str(recipient.id)},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/assistant/ask",
            json={"question": "What is due?", "care_recipient_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )

    after_ids = set(db_session.scalars(select(AIInteractionLog.id)).all())
    assert after_ids == before_ids


def test_logging_failure_does_not_crash_stream(
    client: TestClient,
    assistant_context: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If persisting AIInteractionLog fails, the SSE stream still completes with done."""
    recipient: CareRecipient = assistant_context["recipient"]  # type: ignore[assignment]

    def failing_commit() -> None:
        raise RuntimeError("simulated log write failure")

    # Patch log_interaction_safely's db.add/commit by simulating AIInteractionLog failure via monkeypatch
    original_log_fn = assistant_service.log_interaction_safely

    def wrapped_log(db, question, context_sent, answer, latency_ms):
        monkeypatch.setattr(db, "commit", failing_commit)
        original_log_fn(db, question, context_sent, answer, latency_ms)

    monkeypatch.setattr(assistant_service, "log_interaction_safely", wrapped_log)

    resp = client.post(
        "/api/assistant/ask",
        json={"question": "What is overdue?", "care_recipient_id": str(recipient.id)},
    )
    assert resp.status_code == 200
    events = _parse_sse_stream(resp.text)
    assert events[-1][0] == "done"

