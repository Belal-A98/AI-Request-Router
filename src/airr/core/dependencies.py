"""FastAPI-only dependency adapters; business services do not import HTTP."""
import hmac
from sqlalchemy.exc import SQLAlchemyError
from typing import Annotated
from fastapi import Header, Request
from ..config import Settings
from .problem import APIProblem
from ..modules.sources.service import resolve_source_key


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session_factory(request: Request):
    return request.app.state.sf


def auth_source(request: Request, x_source_key: Annotated[str | None, Header()] = None) -> str:
    if not x_source_key:
        raise APIProblem(401, 'UNAUTHENTICATED', 'Source authentication required')
    if hmac.compare_digest(x_source_key, get_settings(request).source_key):
        return 'default'  # Compatibility with the existing environment credential.
    try:
        source = resolve_source_key(request.app.state.sf, x_source_key)
    except SQLAlchemyError:
        raise APIProblem(503, 'DEPENDENCY_UNAVAILABLE', 'Database not ready')
    if source is None:
        raise APIProblem(401, 'UNAUTHENTICATED', 'Source authentication required')
    if not source.enabled:
        raise APIProblem(403, 'SOURCE_DISABLED', 'Source is disabled')
    return source.id


def auth_reviewer(request: Request, x_reviewer_key: Annotated[str | None, Header()] = None):
    if not x_reviewer_key or not hmac.compare_digest(x_reviewer_key, get_settings(request).reviewer_key):
        raise APIProblem(401, 'UNAUTHENTICATED', 'Reviewer authentication required')
