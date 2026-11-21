"""Serialize the read model without exposing internal payload hashes or secrets."""
from .models import Request


def request_to_dict(request: Request) -> dict:
    return {
        'request_id': request.id,
        'external_id': request.external_id,
        'subject': request.subject,
        'message': request.message,
        'status': request.status,
        'category': request.category,
        'priority': request.priority,
        'reason': request.reason,
        'rejection_reason': request.rejection_reason,
        'classifier_mode': request.classifier_mode,
        'version': request.version,
    }
