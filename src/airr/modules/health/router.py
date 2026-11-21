"""Probes: liveness is app-only, readiness requires the schema."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from ...core.dependencies import get_session_factory
from ...core.problem import APIProblem

router = APIRouter()


@router.get('/health/live')
def live():
    return {'status': 'alive'}


@router.get('/health/ready')
def ready(sf=Depends(get_session_factory)):
    try:
        with sf() as session:
            session.execute(text('SELECT 1 FROM requests LIMIT 1'))
    except Exception:
        raise APIProblem(503, 'DEPENDENCY_UNAVAILABLE', 'Database not ready')
    return {'status': 'ready'}
