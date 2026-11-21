"""Public API error contract and exception mapping."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from .problem import APIProblem


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIProblem)
    async def api_problem(request: Request, exc: APIProblem):
        return JSONResponse(
            status_code=exc.status,
            content={'error': {'code': exc.code, 'message': exc.message},
                     'trace_id': request.state.trace_id},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={'error': {'code': 'INVALID_INPUT', 'message': 'Invalid request fields'},
                     'trace_id': request.state.trace_id},
        )
