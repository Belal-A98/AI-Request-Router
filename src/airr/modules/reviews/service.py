"""Version-guarded human approval/rejection as atomic database updates."""
from sqlalchemy import update
from ...core.problem import APIProblem
from ...core.identifiers import now_utc
from ..audit.models import AuditEvent
from ..delivery.models import Delivery
from ..requests.models import Request
from .schemas import Approval, Rejection


def approve_request(sf, request_id: str, payload: Approval) -> dict:
    with sf.begin() as session:
        changed = session.execute(update(Request).where(
            Request.id == request_id,
            Request.version == payload.expected_version,
            Request.status == 'PENDING_REVIEW',
        ).values(status='APPROVED', category=payload.category, priority=payload.priority,
                 version=Request.version + 1, updated_at=now_utc())).rowcount
        if not changed:
            if session.get(Request, request_id) is None:
                raise APIProblem(404, 'NOT_FOUND', 'Request not found')
            raise APIProblem(409, 'VERSION_CONFLICT', 'Request changed, refresh and retry')
        session.add(Delivery(request_id=request_id, status='PENDING', destination='internal'))
        session.add(AuditEvent(request_id=request_id, event_type='APPROVED', actor_type='reviewer'))
    return {'request_id': request_id, 'status': 'APPROVED'}


def reject_request(sf, request_id: str, payload: Rejection) -> dict:
    with sf.begin() as session:
        changed = session.execute(update(Request).where(
            Request.id == request_id,
            Request.version == payload.expected_version,
            Request.status == 'PENDING_REVIEW',
        ).values(status='REJECTED', rejection_reason=payload.reason,
                 version=Request.version + 1, updated_at=now_utc())).rowcount
        if not changed:
            if session.get(Request, request_id) is None:
                raise APIProblem(404, 'NOT_FOUND', 'Request not found')
            raise APIProblem(409, 'VERSION_CONFLICT', 'Request changed, refresh and retry')
        session.add(AuditEvent(request_id=request_id, event_type='REJECTED', actor_type='reviewer'))
    return {'request_id': request_id, 'status': 'REJECTED'}
