import asyncio
import json
import time
from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AIInteractionLog
from app.services import task_service

MEDICAL_KEYWORDS = [
    "medical advice", "give", "dose", "dosage", "side effect", 
    "diagnose", "symptom", "prescribe", "safe to take", "treatment"
]

def format_local_time(dt: datetime, tz_name: str) -> str:
    local_tz = ZoneInfo(tz_name)
    utc_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(local_tz).strftime("%I:%M %p").lstrip("0")


def serialize_task(task, today_iso: str, tz_name: str) -> dict:
    item = {
        "title": task.title,
        "task_type": task.task_type.value,
        "status": task.status.value,
        "due_at": task.due_at.astimezone(timezone.utc).isoformat(),
    }
    
    local_tz = ZoneInfo(tz_name)
    utc_dt = task.due_at if task.due_at.tzinfo else task.due_at.replace(tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone(local_tz)
    time_text = local_dt.strftime("%I:%M %p").lstrip("0")
    
    if local_dt.date().isoformat() == today_iso:
        item["due_label"] = f"today at {time_text}"
    else:
        item["due_label"] = f"{local_dt.strftime('%b')} {local_dt.day} at {time_text}"

    if task.completed_at:
        item["completed_at"] = task.completed_at.astimezone(timezone.utc).isoformat()
        item["completed_time_label"] = format_local_time(task.completed_at, tz_name)
        item["completed_by_name"] = task.completed_by_name
        
    return item


def build_today_context(db: Session, care_recipient_id: UUID | None = None, now_utc: datetime | None = None) -> dict:
    tz_name = settings.app_timezone
    today = task_service.get_today_tasks(db=db, care_recipient_id=care_recipient_id, now_utc=now_utc, tz_name=tz_name)
    today_iso = today.date.isoformat()

    return {
        "care_recipient_name": today.care_recipient_name,
        "date": today_iso,
        "timezone": tz_name,
        "counts": {
            "overdue": today.counts.overdue,
            "due": today.counts.due,
            "done": today.counts.done,
        },
        "overdue": [serialize_task(t, today_iso, tz_name) for t in today.overdue],
        "due": [serialize_task(t, today_iso, tz_name) for t in today.due],
        "done": [serialize_task(t, today_iso, tz_name) for t in today.done],
    }


def format_task_list(items: list, include_completion: bool = False) -> str:
    parts = []
    for item in items:
        label = str(item["task_type"]).replace("_", "-") 
        
        if include_completion and item.get("completed_time_label"):
            who = item.get("completed_by_name")
            by_text = f"by {who} " if who else ""
            parts.append(f"{item['title']} ({label}, completed {by_text}at {item['completed_time_label']})")
        else:
            parts.append(f"{item['title']} ({label}, due {item['due_label']})")
    return "; ".join(parts)


def generate_answer(question: str, context: dict) -> str:
    q = question.lower().strip()
    recipient = context["care_recipient_name"]
    overdue = context["overdue"]
    due = context["due"]
    done = context["done"]

    if any(keyword in q for keyword in MEDICAL_KEYWORDS):
        return f"I can only share information from today's care schedule for {recipient} and cannot provide medical advice. Please consult a healthcare professional for medical guidance."

    if any(term in q for term in ["tomorrow", "yesterday", "next week", "last week"]):
        return f"I only have access to today's care schedule ({context['date']}) for {recipient}, so I cannot answer about tasks on other dates."

    if any(term in q for term in ["overdue", "late", "missed"]):
        if not overdue:
            return f"There are no overdue tasks for {recipient} right now."
        return f"Overdue for {recipient}: {format_task_list(overdue)}."

    if any(term in q for term in ["completed", "done", "finished"]):
        if not done:
            return f"No tasks have been completed yet today for {recipient}."
        return f"Completed today for {recipient}: {format_task_list(done, include_completion=True)}."

    if not overdue and not due and not done:
        return f"There are no tasks in today's care schedule for {recipient} ({context['date']})."

    summary = [f"Today's schedule for {recipient} ({context['date']}):"]
    if overdue:
        summary.append(f"Overdue: {format_task_list(overdue)}.")
    if due:
        summary.append(f"Due today: {format_task_list(due)}.")
    if done:
        summary.append(f"Completed today: {format_task_list(done, include_completion=True)}.")
    
    return " ".join(summary)



def chunk_answer(answer: str, chunk_size: int = 3) -> list:
    words = answer.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]) + " ")
    return chunks


def format_sse_event(event_name: str, payload: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"


def log_interaction(db: Session, question: str, context: dict, answer: str, latency: int):
    try:
        log = AIInteractionLog(
            question=question,
            context_sent=context,
            answer=answer,
            latency_ms=max(0, latency)
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log interaction: {e}")


async def stream_assistant_response(
    request: Request,
    db: Session,
    question: str,
    care_recipient_id: UUID | None = None,
    now_utc: datetime | None = None,
    chunk_delay: float = 0.02,
):
    start_time = time.time()
    try:
        context_sent = build_today_context(db=db, care_recipient_id=care_recipient_id, now_utc=now_utc)
        answer = generate_answer(question=question, context=context_sent)

        for chunk in chunk_answer(answer):
            if await request.is_disconnected():
                return
            yield format_sse_event("token", {"chunk": chunk})
            if chunk_delay > 0:
                await asyncio.sleep(chunk_delay)

        if await request.is_disconnected():
            return

        latency = int((time.time() - start_time) * 1000)
        log_interaction(db, question, context_sent, answer, latency)
        
        yield format_sse_event("done", {"status": "done"})
        
    except Exception as e:
        print(f"Assistant error: {e}")
        yield format_sse_event(
            "error",
            {"detail": "Unable to generate an answer right now. Please try again."},
        )