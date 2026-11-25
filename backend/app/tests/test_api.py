"""Integration tests for Phase 2 REST APIs and business logic."""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, get_db, get_utc_now
from app.main import app
from app.models import CareRecipient, CareTask, FamilyMember, TaskStatus, TaskType
from app.services import task_service

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
def care_context(db_session: Session) -> dict[str, object]:
    """Create isolated test CareRecipient and FamilyMembers independent of seed data."""
    recipient = CareRecipient(name="Test Parent", date_of_birth=date(1950, 4, 10))
    db_session.add(recipient)
    db_session.flush()

    ravi = FamilyMember(
        care_recipient_id=recipient.id,
        name="Ravi",
        relationship="Son",
    )
    priya = FamilyMember(
        care_recipient_id=recipient.id,
        name="Priya",
        relationship="Daughter",
    )
    db_session.add_all([ravi, priya])
    db_session.commit()

    return {"recipient": recipient, "ravi": ravi, "priya": priya}


def test_create_task_validates_and_persists(
    client: TestClient,
    db_session: Session,
    care_context: dict[str, object],
) -> None:
    """Creating a task validates input, defaults to pending, and persists to DB."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    due_at = (FIXED_NOW_UTC + timedelta(hours=3)).isoformat()

    response = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "  Evening blood pressure check  ",
            "description": "Record systolic and diastolic readings",
            "task_type": "check_in",
            "due_at": due_at,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Evening blood pressure check"
    assert payload["status"] == "pending"
    assert payload["task_type"] == "check_in"
    assert payload["is_overdue"] is False
    assert payload["completed_by_id"] is None
    assert payload["completed_by_name"] is None

    persisted = db_session.get(CareTask, uuid.UUID(payload["id"]))
    assert persisted is not None
    assert persisted.title == "Evening blood pressure check"

    # Missing care recipient returns 404
    missing_recipient_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(uuid.uuid4()),
            "title": "Orphan task",
            "task_type": "medicine",
            "due_at": due_at,
        },
    )
    assert missing_recipient_resp.status_code == 404

    # Naive datetime and blank title return 422
    invalid_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "   ",
            "task_type": "medicine",
            "due_at": "2026-11-25T15:00:00",
        },
    )
    assert invalid_resp.status_code == 422


def test_get_list_and_partial_patch_task(
    client: TestClient,
    care_context: dict[str, object],
) -> None:
    """List filters, single-task retrieval, and partial PATCH semantics work as expected."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    create_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "Morning medicine",
            "description": "Initial note",
            "task_type": "medicine",
            "due_at": (FIXED_NOW_UTC + timedelta(hours=1)).isoformat(),
        },
    )
    task_id = create_resp.json()["id"]

    list_resp = client.get(
        "/api/tasks",
        params={"status": "pending", "task_type": "medicine", "care_recipient_id": str(recipient.id)},
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    get_resp = client.get(f"/api/tasks/{task_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Morning medicine"

    patch_resp = client.patch(
        f"/api/tasks/{task_id}",
        json={"title": "Updated morning medicine", "description": None},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Updated morning medicine"
    assert patch_resp.json()["description"] is None
    assert patch_resp.json()["status"] == "pending"

    # Attempting to modify status or audit fields via PATCH is rejected with 422
    forbidden_patch = client.patch(
        f"/api/tasks/{task_id}",
        json={"status": "done"},
    )
    assert forbidden_patch.status_code == 422

    # Missing task returns 404
    assert client.get(f"/api/tasks/{uuid.uuid4()}").status_code == 404


def test_today_groups_overdue_due_and_done_with_deterministic_timestamps(
    client: TestClient,
    db_session: Session,
    care_context: dict[str, object],
) -> None:
    """Today endpoint accurately groups overdue, due, and done tasks in app timezone."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    ravi: FamilyMember = care_context["ravi"]  # type: ignore[assignment]

    # 1. Overdue from yesterday (pending)
    overdue_yesterday = CareTask(
        care_recipient_id=recipient.id,
        title="Yesterday missed check-in",
        task_type=TaskType.CHECK_IN,
        due_at=FIXED_NOW_UTC - timedelta(days=1),
        status=TaskStatus.PENDING,
    )
    # 2. Overdue from earlier today (pending)
    overdue_earlier_today = CareTask(
        care_recipient_id=recipient.id,
        title="Morning medicine overdue",
        task_type=TaskType.MEDICINE,
        due_at=FIXED_NOW_UTC - timedelta(hours=2),
        status=TaskStatus.PENDING,
    )
    # 3. Due later today (pending)
    due_later_today = CareTask(
        care_recipient_id=recipient.id,
        title="Evening medicine due",
        task_type=TaskType.MEDICINE,
        due_at=FIXED_NOW_UTC + timedelta(hours=4),
        status=TaskStatus.PENDING,
    )
    # 4. Due tomorrow (pending - excluded from today)
    due_tomorrow = CareTask(
        care_recipient_id=recipient.id,
        title="Tomorrow appointment",
        task_type=TaskType.APPOINTMENT,
        due_at=FIXED_NOW_UTC + timedelta(days=1),
        status=TaskStatus.PENDING,
    )
    # 5. Completed today even though originally due yesterday -> must appear in done
    done_today_from_yesterday = CareTask(
        care_recipient_id=recipient.id,
        title="Caught up yesterday task",
        task_type=TaskType.APPOINTMENT,
        due_at=FIXED_NOW_UTC - timedelta(days=1),
        status=TaskStatus.DONE,
        completed_by_id=ravi.id,
        completed_at=FIXED_NOW_UTC - timedelta(hours=1),
    )
    # 6. Completed yesterday -> excluded from today's done
    done_yesterday = CareTask(
        care_recipient_id=recipient.id,
        title="Yesterday completed check-in",
        task_type=TaskType.CHECK_IN,
        due_at=FIXED_NOW_UTC - timedelta(days=1),
        status=TaskStatus.DONE,
        completed_by_id=ravi.id,
        completed_at=FIXED_NOW_UTC - timedelta(days=1),
    )
    db_session.add_all(
        [
            overdue_yesterday,
            overdue_earlier_today,
            due_later_today,
            due_tomorrow,
            done_today_from_yesterday,
            done_yesterday,
        ]
    )
    db_session.commit()

    response = client.get("/api/today", params={"care_recipient_id": str(recipient.id)})
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2026-11-25"
    assert data["care_recipient_id"] == str(recipient.id)
    assert data["care_recipient_name"] == "Test Parent"
    assert [t["title"] for t in data["overdue"]] == [
        "Yesterday missed check-in",
        "Morning medicine overdue",
    ]
    assert all(t["is_overdue"] is True for t in data["overdue"])
    assert [t["title"] for t in data["due"]] == ["Evening medicine due"]
    assert [t["title"] for t in data["done"]] == ["Caught up yesterday task"]
    assert data["done"][0]["completed_by_name"] == "Ravi"
    assert data["counts"] == {"overdue": 2, "due": 1, "done": 1}


def test_today_timezone_boundary_conversion(
    db_session: Session,
    care_context: dict[str, object],
) -> None:
    """Verify local day boundaries in a non-UTC timezone convert accurately to UTC."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    ravi: FamilyMember = care_context["ravi"]  # type: ignore[assignment]

    # 2026-11-25 19:00 UTC == 2026-11-26 00:30 IST (Asia/Kolkata, UTC+05:30)
    now_utc = datetime(2026, 11, 25, 19, 0, 0, tzinfo=timezone.utc)

    # Due 2026-11-26 23:30 IST -> 2026-11-26 18:00 UTC (same local day -> due)
    due_before_ist_midnight = CareTask(
        care_recipient_id=recipient.id,
        title="Late IST task",
        task_type=TaskType.CHECK_IN,
        due_at=datetime(2026, 11, 26, 18, 0, 0, tzinfo=timezone.utc),
        status=TaskStatus.PENDING,
    )
    # Due 2026-11-27 00:30 IST -> 2026-11-26 19:00 UTC (next local day -> excluded)
    due_after_ist_midnight = CareTask(
        care_recipient_id=recipient.id,
        title="Next IST day task",
        task_type=TaskType.CHECK_IN,
        due_at=datetime(2026, 11, 26, 19, 0, 0, tzinfo=timezone.utc),
        status=TaskStatus.PENDING,
    )
    # Completed 2026-11-26 00:15 IST -> 2026-11-25 18:45 UTC (today in IST -> done)
    done_after_ist_midnight = CareTask(
        care_recipient_id=recipient.id,
        title="Early IST completion",
        task_type=TaskType.MEDICINE,
        due_at=datetime(2026, 11, 25, 18, 0, 0, tzinfo=timezone.utc),
        status=TaskStatus.DONE,
        completed_by_id=ravi.id,
        completed_at=datetime(2026, 11, 25, 18, 45, 0, tzinfo=timezone.utc),
    )
    db_session.add_all(
        [due_before_ist_midnight, due_after_ist_midnight, done_after_ist_midnight]
    )
    db_session.commit()

    today_view = task_service.get_today_tasks(
        db=db_session,
        care_recipient_id=recipient.id,
        now_utc=now_utc,
        tz_name="Asia/Kolkata",
    )
    assert today_view.date == date(2026, 11, 26)
    assert [t.title for t in today_view.due] == ["Late IST task"]
    assert [t.title for t in today_view.done] == ["Early IST completion"]
    assert today_view.counts.overdue == 0


def test_complete_task_records_member_and_timestamp(
    client: TestClient,
    care_context: dict[str, object],
) -> None:
    """Completing a pending task records status, member name, and server UTC timestamp."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    priya: FamilyMember = care_context["priya"]  # type: ignore[assignment]

    create_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "Afternoon pill",
            "task_type": "medicine",
            "due_at": (FIXED_NOW_UTC - timedelta(minutes=30)).isoformat(),
        },
    )
    task_id = create_resp.json()["id"]
    assert create_resp.json()["is_overdue"] is True

    complete_resp = client.post(
        f"/api/tasks/{task_id}/complete",
        json={"completed_by_id": str(priya.id)},
    )
    assert complete_resp.status_code == 200
    body = complete_resp.json()
    assert body["status"] == "done"
    assert body["is_overdue"] is False
    assert body["completed_by_id"] == str(priya.id)
    assert body["completed_by_name"] == "Priya"
    assert datetime.fromisoformat(body["completed_at"]) == FIXED_NOW_UTC


def test_invalid_family_member_or_missing_task(
    client: TestClient,
    db_session: Session,
    care_context: dict[str, object],
) -> None:
    """Missing task/member returns 404; member from another care recipient returns 400."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    priya: FamilyMember = care_context["priya"]  # type: ignore[assignment]

    other_recipient = CareRecipient(name="Other Parent")
    db_session.add(other_recipient)
    db_session.flush()
    other_member = FamilyMember(
        care_recipient_id=other_recipient.id,
        name="Meera",
        relationship="Daughter",
    )
    db_session.add(other_member)
    db_session.commit()

    create_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "Check-in",
            "task_type": "check_in",
            "due_at": FIXED_NOW_UTC.isoformat(),
        },
    )
    task_id = create_resp.json()["id"]

    # Missing task -> 404
    assert (
        client.post(
            f"/api/tasks/{uuid.uuid4()}/complete",
            json={"completed_by_id": str(priya.id)},
        ).status_code
        == 404
    )

    # Missing family member -> 404
    assert (
        client.post(
            f"/api/tasks/{task_id}/complete",
            json={"completed_by_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )

    # Family member belonging to another care recipient -> 400
    cross_resp = client.post(
        f"/api/tasks/{task_id}/complete",
        json={"completed_by_id": str(other_member.id)},
    )
    assert cross_resp.status_code == 400


def test_completing_already_completed_task_returns_409(
    client: TestClient,
    care_context: dict[str, object],
) -> None:
    """A second completion attempt returns 409 and preserves original audit info."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    priya: FamilyMember = care_context["priya"]  # type: ignore[assignment]
    ravi: FamilyMember = care_context["ravi"]  # type: ignore[assignment]

    create_resp = client.post(
        "/api/tasks",
        json={
            "care_recipient_id": str(recipient.id),
            "title": "Doctor follow-up",
            "task_type": "appointment",
            "due_at": FIXED_NOW_UTC.isoformat(),
        },
    )
    task_id = create_resp.json()["id"]

    first = client.post(
        f"/api/tasks/{task_id}/complete",
        json={"completed_by_id": str(priya.id)},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/tasks/{task_id}/complete",
        json={"completed_by_id": str(ravi.id)},
    )
    assert second.status_code == 409

    # Original audit record remains intact
    fetched = client.get(f"/api/tasks/{task_id}").json()
    assert fetched["completed_by_id"] == str(priya.id)
    assert fetched["completed_by_name"] == "Priya"
    assert fetched["completed_at"] == first.json()["completed_at"]


def test_concurrent_task_completion_race_safety() -> None:
    """Verify PostgreSQL atomic conditional update allows exactly one winner and raises 409 for loser."""
    with SessionLocal() as db:
        recipient = CareRecipient(name=f"Concurrent Parent {uuid.uuid4()}")
        db.add(recipient)
        db.flush()
        member_a = FamilyMember(
            care_recipient_id=recipient.id,
            name="Member A",
            relationship="Son",
        )
        member_b = FamilyMember(
            care_recipient_id=recipient.id,
            name="Member B",
            relationship="Daughter",
        )
        db.add_all([member_a, member_b])
        db.flush()
        task = CareTask(
            care_recipient_id=recipient.id,
            title="Concurrent completion task",
            task_type=TaskType.MEDICINE,
            due_at=FIXED_NOW_UTC,
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        recipient_id = recipient.id
        task_id = task.id
        member_a_id = member_a.id
        member_b_id = member_b.id

    barrier = threading.Barrier(2)

    def attempt_complete(member_id: uuid.UUID) -> str:
        barrier.wait(timeout=5)
        with SessionLocal() as worker_db:
            try:
                res = task_service.complete_task(
                    db=worker_db,
                    task_id=task_id,
                    completed_by_id=member_id,
                    now_utc=FIXED_NOW_UTC,
                )
                return f"ok:{res.completed_by_id}"
            except HTTPException as exc:
                if exc.status_code == 409:
                    return "conflict"
                raise

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt_complete, [member_a_id, member_b_id]))

        ok_outcomes = [o for o in outcomes if o.startswith("ok:")]
        conflict_outcomes = [o for o in outcomes if o == "conflict"]
        assert len(ok_outcomes) == 1
        assert len(conflict_outcomes) == 1
    finally:
        with SessionLocal() as cleanup_db:
            persisted = cleanup_db.scalar(
                select(CareRecipient).where(CareRecipient.id == recipient_id)
            )
            if persisted is not None:
                cleanup_db.delete(persisted)
                cleanup_db.commit()


def test_family_members_endpoint(
    client: TestClient,
    care_context: dict[str, object],
) -> None:
    """GET /api/family-members returns members for the requested care recipient."""
    recipient: CareRecipient = care_context["recipient"]  # type: ignore[assignment]
    resp = client.get(
        "/api/family-members",
        params={"care_recipient_id": str(recipient.id)},
    )
    assert resp.status_code == 200
    members = resp.json()
    assert [(m["name"], m["relationship"]) for m in members] == [
        ("Priya", "Daughter"),
        ("Ravi", "Son"),
    ]

    assert (
        client.get(
            "/api/family-members",
            params={"care_recipient_id": str(uuid.uuid4())},
        ).status_code
        == 404
    )


def test_unexpected_server_error_hides_internal_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unhandled exceptions return HTTP 500 without leaking internal error details."""

    def boom(*_args, **_kwargs):
        raise RuntimeError("sensitive internal db connection string")

    monkeypatch.setattr(task_service, "list_tasks", boom)
    response = client.get("/api/tasks")
    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected internal server error occurred."}
    assert "sensitive" not in response.text
