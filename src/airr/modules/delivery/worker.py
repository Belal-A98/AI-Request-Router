"""Internal delivery only; no external HTTP side effects in this stage."""
from ..audit.models import AuditEvent
from ..jobs.claims import claim_next
from ..requests.models import Request
from .models import Delivery


def process_delivery_once(sf):
    with sf.begin() as session:
        claim = claim_next(session, Delivery)
    if claim is None:
        return False
    delivery_id, request_id = claim
    with sf.begin() as session:
        delivery = session.get(Delivery, delivery_id)
        request = session.get(Request, request_id)
        if delivery.status != 'CLAIMED':
            return False
        if delivery.destination != 'internal':
            delivery.status = 'UNKNOWN'
            request.status = 'DELIVERY_UNKNOWN'
            session.add(AuditEvent(request_id=request.id, event_type='DELIVERY_UNKNOWN', actor_type='worker'))
            return True
        delivery.status = 'SENT'
        request.status = 'COMPLETED'
        session.add(AuditEvent(request_id=request.id, event_type='DELIVERED_INTERNAL', actor_type='worker'))
    return True
