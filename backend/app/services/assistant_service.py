import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AIInteractionLog
from app.schemas.task import TaskResponse
from app.services import task_service

logger = logging.getLogger(__name__)

_TYPE_LABELS = {
    "medicine": "medicine",
    "appointment": "appointment",
    "check_in": "check-in",
}

_MEDICAL_ADVICE_PATTERNS = (
    r"\bmedical advice\b",
    r"\bshould i give\b",
    r"\bchange (?:the )?dos(?:e|age)\b",
    r"\bincrease (?:the )?dos(?:e|age)\b",
    r"\bdecrease (?:the )?dos(?:e|age)\b",
    r"\bside effects?\b",
    r"\bdiagnos(?:e|is)\b",
    r"\bsymptoms?\b",
    r"\bprescrib(?:e|ed|ing)\b",
    r"\bsafe to take\b",
    r"\btreatment\b",
)

_STOP_WORDS = {
    "a", "about", "all", "am", "an", "and", "any", "are", "at", "be", "been",
    "but", "by", "can", "could", "did", "do", "does", "done", "due", "for",
    "from", "get", "give", "given", "had", "has", "have", "help", "her", "his",
    "how", "in", "is", "it", "know", "last", "left", "listed", "me", "missed",
    "mum", "need", "needs", "not", "of", "on", "or", "our", "overdue",
    "pending", "please", "remaining", "schedule", "scheduled", "see", "she",
    "show", "status", "still", "summary", "take", "taken", "taking", "task",
    "tasks", "tell", "the", "their", "there", "this", "to", "today", "todays",
    "was", "were", "what", "when", "where", "which", "who", "will", "with",
    "would",
}


def _format_local_time(dt: datetime, local_tz: ZoneInfo) -> str:
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(local_tz).strftime("%I:%M %p").lstrip("0")


def _format_local_due(dt: datetime, today_iso: str, local_tz: ZoneInfo) -> str:
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone(local_tz)
    time_text = local_dt.strftime("%I:%M %p").lstrip("0")
    if local_dt.date().isoformat() == today_iso:
        return f"today at {time_text}"
    return f"{local_dt.strftime('%b')} {local_dt.day} at {time_text}"


def _serialize_task(task: TaskResponse, today_iso: str, local_tz: ZoneInfo) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": task.title,
        "task_type": task.task_type.value,
        "status": task.status.value,
        "due_at": task.due_at.astimezone(timezone.utc).isoformat(),
        "due_label": _format_local_due(task.due_at, today_iso, local_tz),
    }
    if task.completed_at is not None:
        item["completed_at"] = task.completed_at.astimezone(timezone.utc).isoformat()
        item["completed_time_label"] = _format_local_time(task.completed_at, local_tz)
        item["completed_by_name"] = task.completed_by_name
    return item


def build_today_context(
    db: Session,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
    tz_name: str | None = None,
) -> dict[str, Any]:
    resolved_tz_name = tz_name or get_settings().app_timezone
    local_tz = ZoneInfo(resolved_tz_name)

    today = task_service.get_today_tasks(
        db=db,
        care_recipient_id=care_recipient_id,
        now_utc=now_utc,
        tz_name=resolved_tz_name,
    )
    today_iso = today.date.isoformat()

    return {
        "care_recipient_name": today.care_recipient_name,
        "date": today_iso,
        "timezone": resolved_tz_name,
        "counts": {
            "overdue": today.counts.overdue,
            "due": today.counts.due,
            "done": today.counts.done,
        },
        "overdue": [_serialize_task(t, today_iso, local_tz) for t in today.overdue],
        "due": [_serialize_task(t, today_iso, local_tz) for t in today.due],
        "done": [_serialize_task(t, today_iso, local_tz) for t in today.done],
    }


def _format_task_list(items: list[dict[str, Any]], include_completion: bool = False) -> str:
    parts: list[str] = []
    for item in items:
        label = _TYPE_LABELS.get(item["task_type"], item["task_type"])
        if include_completion and item.get("completed_time_label"):
            who = item.get("completed_by_name")
            by_text = f"by {who} " if who else ""
            parts.append(
                f"{item['title']} ({label}, completed {by_text}at {item['completed_time_label']})"
            )
        else:
            parts.append(f"{item['title']} ({label}, due {item['due_label']})")
    return "; ".join(parts)


def _unknown_words(question_lower: str, context: dict[str, Any]) -> list[str]:
    known = {
        "medicine", "medicines", "medication", "medications", "meds", "pill", "pills",
        "appointment", "appointments", "doctor", "check", "checkin", "check-in",
        "call", "calls", "care", "person", "anyone", "anything", "everything",
        "completed", "finished", "today", "overdue", "late", "due", "done", "pending",
        context["care_recipient_name"].lower(),
    }
    for bucket in ("overdue", "due", "done"):
        for item in context[bucket]:
            known.update(re.findall(r"[a-z0-9]+", item["title"].lower()))
            if item.get("completed_by_name"):
                known.update(re.findall(r"[a-z0-9]+", item["completed_by_name"].lower()))

    words = re.findall(r"[a-z0-9]+", question_lower)
    return [w for w in words if w not in _STOP_WORDS and w not in known and len(w) > 2]


def generate_answer(question: str, context: dict[str, Any]) -> str:
    q = question.lower().strip()
    recipient = context["care_recipient_name"]
    overdue: list[dict[str, Any]] = context["overdue"]
    due: list[dict[str, Any]] = context["due"]
    done: list[dict[str, Any]] = context["done"]

    if any(re.search(pattern, q) for pattern in _MEDICAL_ADVICE_PATTERNS):
        return (
            f"I can only share information from today's care schedule for {recipient} "
            "and cannot provide medical advice. Please consult a healthcare professional "
            "for medical guidance."
        )

    if any(term in q for term in ("tomorrow", "yesterday", "next week", "last week")):
        return (
            f"I only have access to today's care schedule ({context['date']}) for {recipient}, "
            "so I cannot answer about tasks on other dates."
        )

    categories = (
        ("medicine", ("medicine", "medicines", "medication", "medications", "meds", "pill", "pills"), "medicine tasks"),
        ("appointment", ("appointment", "appointments", "doctor"), "appointments"),
        ("check_in", ("check-in", "check in", "checkin", "call", "calls"), "check-in tasks"),
    )
    for task_type, keywords, label_plural in categories:
        if any(kw in q for kw in keywords):
            cat_overdue = [t for t in overdue if t["task_type"] == task_type]
            cat_due = [t for t in due if t["task_type"] == task_type]
            cat_done = [t for t in done if t["task_type"] == task_type]

            if not (cat_overdue or cat_due or cat_done):
                return f"There are no {label_plural} in today's care schedule for {recipient}."

            asking_done = any(w in q for w in ("all", "completed", "done", "finished"))
            parts: list[str] = []
            if asking_done and not cat_overdue and not cat_due:
                parts.append(
                    f"Yes, all {label_plural} in today's schedule for {recipient} are completed: "
                    f"{_format_task_list(cat_done, include_completion=True)}."
                )
            else:
                if asking_done:
                    parts.append(f"Not all {label_plural} for {recipient} are completed yet.")
                if cat_overdue:
                    parts.append(f"Overdue: {_format_task_list(cat_overdue)}.")
                if cat_due:
                    parts.append(f"Due today: {_format_task_list(cat_due)}.")
                if cat_done:
                    parts.append(f"Completed today: {_format_task_list(cat_done, include_completion=True)}.")
            return " ".join(parts)

    if any(term in q for term in ("who", "last task", "latest", "recent")):
        if not done:
            return f"No tasks have been completed yet today for {recipient}."
        latest = done[0]
        who = latest.get("completed_by_name")
        time_label = latest.get("completed_time_label") or "an earlier time today"
        if who:
            return f"The most recently completed task today is \"{latest['title']}\", completed by {who} at {time_label}."
        return f"The most recently completed task today is \"{latest['title']}\", completed at {time_label} (the family member was not recorded)."

    if any(term in q for term in ("overdue", "late", "missed", "behind", "past due")):
        if not overdue:
            return f"There are no overdue tasks for {recipient} right now."
        return f"Overdue for {recipient}: {_format_task_list(overdue)}."

    if any(term in q for term in ("still", "remaining", "need", "left", "pending", "to do", "todo")):
        if not overdue and not due:
            return f"Everything on {recipient}'s schedule for today is complete. There are no overdue or pending tasks remaining."
        parts = []
        if overdue:
            parts.append(f"Overdue: {_format_task_list(overdue)}.")
        if due:
            parts.append(f"Due today: {_format_task_list(due)}.")
        return " ".join(parts)

    if any(term in q for term in ("completed", "done", "finished")):
        if not done:
            return f"No tasks have been completed yet today for {recipient}."
        return f"Completed today for {recipient}: {_format_task_list(done, include_completion=True)}."

    if "due" in q:
        if not due and not overdue:
            return f"There are no tasks due for {recipient} today."
        parts = [f"Due today: {_format_task_list(due)}."] if due else [
            f"No upcoming tasks remain due later today for {recipient}."
        ]
        if overdue:
            parts.append(f"Overdue from earlier: {_format_task_list(overdue)}.")
        return " ".join(parts)

    if _unknown_words(q, context):
        return (
            f"I don't have information about that in today's care schedule for {recipient} "
            f"({context['date']}). Currently there are {len(overdue)} overdue, {len(due)} due today, "
            f"and {len(done)} completed task(s)."
        )

    if not overdue and not due and not done:
        return f"There are no tasks in today's care schedule for {recipient} ({context['date']})."

    summary = [f"Today's schedule for {recipient} ({context['date']}):"]
    if overdue:
        summary.append(f"Overdue: {_format_task_list(overdue)}.")
    if due:
        summary.append(f"Due today: {_format_task_list(due)}.")
    if done:
        summary.append(f"Completed today: {_format_task_list(done, include_completion=True)}.")
    return " ".join(summary)


def chunk_answer(answer: str, words_per_chunk: int = 3) -> list[str]:
    tokens = re.findall(r"\S+\s*", answer)
    if not tokens:
        return [answer] if answer else []
    return ["".join(tokens[i : i + words_per_chunk]) for i in range(0, len(tokens), words_per_chunk)]


def format_sse_event(event_name: str, payload: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def log_interaction_safely(
    db: Session,
    question: str,
    context_sent: dict[str, Any],
    answer: str,
    latency_ms: int,
) -> None:
    try:
        db.add(
            AIInteractionLog(
                question=question,
                context_sent=context_sent,
                answer=answer,
                latency_ms=max(0, latency_ms),
            )
        )
        db.commit()
    except Exception:
        logger.exception("Failed to save AIInteractionLog")
        try:
            db.rollback()
        except Exception:
            logger.exception("Failed to rollback session after logging error")


async def stream_assistant_response(
    request: Request,
    db: Session,
    question: str,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
    chunk_delay_seconds: float = 0.02,
) -> AsyncGenerator[str, None]:
    start_time = time.perf_counter()
    try:
        context_sent = build_today_context(db=db, care_recipient_id=care_recipient_id, now_utc=now_utc)
        answer = generate_answer(question=question, context=context_sent)

        for chunk in chunk_answer(answer):
            if await request.is_disconnected():
                return
            yield format_sse_event("token", {"chunk": chunk})
            if chunk_delay_seconds > 0:
                await asyncio.sleep(chunk_delay_seconds)

        if await request.is_disconnected():
            return

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_interaction_safely(
            db=db,
            question=question,
            context_sent=context_sent,
            answer=answer,
            latency_ms=latency_ms,
        )
        yield format_sse_event("done", {"status": "done"})
    except Exception as exc:
        logger.exception("Assistant stream error: %s", exc)
        yield format_sse_event(
            "error",
            {"detail": "Unable to generate an answer right now. Please try again."},
        )
