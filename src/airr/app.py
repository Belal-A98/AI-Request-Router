"""Application composition root: wire configuration, adapters and routers only."""
from fastapi import FastAPI
from .config import Settings
from .core.errors import install_error_handlers
from .core.observability import install_http_middleware
from .db import make_engine, make_session_factory
from .modules.health.router import router as health_router
from .modules.requests.router import router as requests_router
from .modules.reviews.router import router as reviews_router
from .modules.webhooks.router import router as webhooks_router


def create_app(settings: Settings | None = None, session_factory=None) -> FastAPI:
    settings = settings or Settings.from_env()
    if session_factory is None:
        session_factory = make_session_factory(make_engine(settings.db_url))
    app = FastAPI(title='AI Request Router', version='0.1.0',
                  description='Deterministic rules mode verified. LLM and outbound HTTP are NOT enabled.')
    app.state.settings = settings
    app.state.sf = session_factory
    install_error_handlers(app)
    install_http_middleware(app)
    app.include_router(health_router)
    app.include_router(requests_router)
    app.include_router(reviews_router)
    app.include_router(webhooks_router)
    return app
