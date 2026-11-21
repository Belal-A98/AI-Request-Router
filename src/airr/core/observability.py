"""One correlation ID per HTTP request, including early size rejections."""
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BODY_LIMIT_BYTES = 65536


def install_http_middleware(app: FastAPI) -> None:
    @app.middleware('http')
    async def limits_and_trace(request: Request, call_next):
        request.state.trace_id = str(uuid.uuid4())
        if request.headers.get('content-length'):
            try:
                if int(request.headers['content-length']) > BODY_LIMIT_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={'error': {'code': 'BODY_TOO_LARGE',
                                           'message': 'Maximum body size exceeded'},
                                 'trace_id': request.state.trace_id},
                        headers={'X-Trace-Id': request.state.trace_id},
                    )
            except ValueError:
                pass
        response = await call_next(request)
        response.headers['X-Trace-Id'] = request.state.trace_id
        return response
