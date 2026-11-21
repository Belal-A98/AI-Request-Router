"""Claim and complete one durable classification job."""
from ..audit.models import AuditEvent
from ..jobs.claims import claim_next
from ..jobs.models import Job
from ..requests.models import Request
from .rules import classify


def process_classification_once(sf):
    with sf.begin() as session:
        claim = claim_next(session, Job)
    if claim is None:
        return False
    job_id, request_id = claim
    with sf() as session:
        request = session.get(Request, request_id)
        if not request:
            return False
        proposal = classify(request.subject, request.message)
    with sf.begin() as session:
        job = session.get(Job, job_id)
        request = session.get(Request, request_id)
        if job.status != 'CLAIMED':
            return False
        if request.status != 'RECEIVED':
            job.status = 'DONE'
            return True
        request.category = proposal.category
        request.priority = proposal.priority
        request.reason = proposal.reason
        request.classifier_mode = proposal.mode
        request.version += 1
        request.status = 'PENDING_REVIEW'
        job.status = 'DONE'
        session.add(AuditEvent(request_id=request.id, event_type='CLASSIFIED', actor_type='worker'))
    return True
