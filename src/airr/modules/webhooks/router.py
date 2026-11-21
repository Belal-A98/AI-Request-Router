"""HMAC-authenticated webhook intake; delegates persistence to requests service."""
import hashlib
import hmac
import time
from typing import Annotated
from fastapi import APIRouter, Header, Request
from ...core.problem import APIProblem
from ...core.observability import BODY_LIMIT_BYTES
from ..requests.schemas import Intake
from ..requests.service import create_request

router = APIRouter()


@router.post('/api/v1/webhooks/intake', status_code=202)
async def signed_webhook(request: Request,
                         x_timestamp: Annotated[str | None, Header()] = None,
                         x_signature: Annotated[str | None, Header()] = None):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > BODY_LIMIT_BYTES:
            raise APIProblem(413, 'BODY_TOO_LARGE', 'Maximum body size exceeded')
        body.extend(chunk)
    raw = bytes(body)
    try:
        timestamp = int(x_timestamp or '')
    except (TypeError, ValueError):
        raise APIProblem(401, 'UNAUTHENTICATED', 'Invalid webhook signature or timestamp')
    if abs(time.time() - timestamp) > 300 or not x_signature or not x_signature.startswith('sha256='):
        raise APIProblem(401, 'UNAUTHENTICATED', 'Invalid webhook signature or timestamp')
    settings = request.app.state.settings
    expected = hmac.new(settings.source_key.encode(), str(timestamp).encode() + b'.' + raw,
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(x_signature.split('=', 1)[1], expected):
        raise APIProblem(401, 'UNAUTHENTICATED', 'Invalid webhook signature or timestamp')
    try:
        payload = Intake.model_validate_json(raw)
    except Exception:
        raise APIProblem(422, 'INVALID_INPUT', 'Invalid request fields')
    return create_request(request.app.state.sf, payload)
