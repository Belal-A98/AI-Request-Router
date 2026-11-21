"""Request persistence and read operations. No HTTP/framework dependency here."""
import hashlib
import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from ...core.problem import APIProblem
from ..audit.models import AuditEvent
from ..jobs.models import Job
from .models import Request
from .schemas import Intake
from .serialization import request_to_dict

CATEGORIES = frozenset({"sales", "support", "billing", "other"})


def payload_digest(payload: Intake) -> str:
    raw = json.dumps(
        payload.model_dump(), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def create_request(sf, payload: Intake, source_id: str = "default") -> dict:
    """Persist the request, classification job and event atomically."""
    content_hash = payload_digest(payload)
    try:
        with sf.begin() as session:
            existing = session.scalar(
                select(Request).where(
                    Request.source_id == source_id,
                    Request.external_id == payload.external_id,
                )
            )
            if existing is not None:
                if existing.payload_hash != content_hash:
                    raise APIProblem(
                        409, "IDEMPOTENCY_CONFLICT",
                        "Identifier already used with different content",
                    )
                return {"request_id": existing.id, "status": existing.status}
            record = Request(
                external_id=payload.external_id,
                source_id=source_id,
                subject=payload.subject,
                message=payload.message,
                payload_hash=content_hash,
                status="RECEIVED",
            )
            session.add(record)
            session.flush()
            session.add(Job(request_id=record.id, kind="classify", status="PENDING"))
            session.add(
                AuditEvent(
                    request_id=record.id,
                    event_type="RECEIVED",
                    actor_type="source",
                )
            )
            request_id = record.id
        return {"request_id": request_id, "status": "RECEIVED"}
    except IntegrityError:
        try:
            with sf() as session:
                existing = session.scalar(
                    select(Request).where(
                        Request.source_id == source_id,
                        Request.external_id == payload.external_id,
                    )
                )
                if existing is None:
                    raise APIProblem(
                        503, "DEPENDENCY_UNAVAILABLE",
                        "Race could not be reconciled",
                    )
                if existing.payload_hash != content_hash:
                    raise APIProblem(
                        409, "IDEMPOTENCY_CONFLICT",
                        "Identifier already used with different content",
                    )
                return {"request_id": existing.id, "status": existing.status}
        except OperationalError:
            raise APIProblem(503, "DEPENDENCY_UNAVAILABLE", "Database not ready")
    except OperationalError:
        raise APIProblem(503, "DEPENDENCY_UNAVAILABLE", "Database not ready")


def list_requests(
    sf,
    limit: int,
    offset: int,
    status: str | None,
    category: str | None = None,
) -> dict:
    if not 1 <= limit <= 100 or offset < 0:
        raise APIProblem(422, "INVALID_INPUT", "Invalid pagination")
    if category is not None and category not in CATEGORIES:
        raise APIProblem(422, "INVALID_INPUT", "Unsupported category")
    try:
        with sf() as session:
            query = select(Request)
            if status:
                query = query.where(Request.status == status)
            if category is not None:
                query = query.where(Request.category == category)
            rows = session.scalars(
                query.order_by(Request.created_at.desc(), Request.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return {"items": [request_to_dict(row) for row in rows]}
    except OperationalError:
        raise APIProblem(503, "DEPENDENCY_UNAVAILABLE", "Database not ready")


def get_request(sf, request_id: str) -> dict:
    with sf() as session:
        request = session.get(Request, request_id)
        if request is None:
            raise APIProblem(404, "NOT_FOUND", "Request not found")
        return request_to_dict(request)


def get_request_events(sf, request_id: str) -> dict:
    with sf() as session:
        if session.get(Request, request_id) is None:
            raise APIProblem(404, "NOT_FOUND", "Request not found")
        events = session.scalars(
            select(AuditEvent).where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.created_at, AuditEvent.id)
        ).all()
        return {
            "items": [
                {
                    "event_type": event.event_type,
                    "actor_type": event.actor_type,
                    "created_at": event.created_at.isoformat(),
                }
                for event in events
            ]
        }
