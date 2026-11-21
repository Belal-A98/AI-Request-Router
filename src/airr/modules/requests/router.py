"""Authenticated HTTP endpoints for request ingestion and read-only queries."""
from typing import Literal

from fastapi import APIRouter, Depends

from ...core.dependencies import auth_reviewer, auth_source, get_session_factory
from .schemas import Intake
from .service import (
    create_request,
    get_request,
    get_request_events,
    list_requests as list_request_records,
)

router = APIRouter()

Category = Literal["sales", "support", "billing", "other"]


@router.post("/api/v1/requests", status_code=202)
def intake(
    payload: Intake,
    source_id: str = Depends(auth_source),
    sf=Depends(get_session_factory),
):
    return create_request(sf, payload, source_id=source_id)


@router.get("/api/v1/requests", dependencies=[Depends(auth_reviewer)])
def list_requests(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
    category: Category | None = None,
    sf=Depends(get_session_factory),
):
    return list_request_records(sf, limit, offset, status, category)


@router.get("/api/v1/requests/{request_id}", dependencies=[Depends(auth_reviewer)])
def detail(request_id: str, sf=Depends(get_session_factory)):
    return get_request(sf, request_id)


@router.get("/api/v1/requests/{request_id}/events", dependencies=[Depends(auth_reviewer)])
def request_events(request_id: str, sf=Depends(get_session_factory)):
    return get_request_events(sf, request_id)
