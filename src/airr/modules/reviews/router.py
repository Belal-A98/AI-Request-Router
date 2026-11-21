"""Reviewer-only decisions; no business rules inside route handlers."""
from fastapi import APIRouter, Depends
from ...core.dependencies import auth_reviewer, get_session_factory
from .schemas import Approval, Rejection
from .service import approve_request, reject_request

router = APIRouter(dependencies=[Depends(auth_reviewer)])


@router.post('/api/v1/requests/{request_id}/approve')
def approve(request_id: str, payload: Approval, sf=Depends(get_session_factory)):
    return approve_request(sf, request_id, payload)


@router.post('/api/v1/requests/{request_id}/reject')
def reject(request_id: str, payload: Rejection, sf=Depends(get_session_factory)):
    return reject_request(sf, request_id, payload)
