"""Reusable isolated SQLite fixtures for public regression tests."""
import pytest
from fastapi.testclient import TestClient

import airr.models  # Register model metadata before creating test tables.
from airr.app import create_app
from airr.config import Settings
from airr.db import Base, make_engine, make_session_factory


@pytest.fixture
def app(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'requests.sqlite'}"
    engine = make_engine(db_url)
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    settings = Settings(
        source_key="public-test-source-key-0123456789",
        reviewer_key="public-test-reviewer-key-9876543210",
        db_url=db_url,
    )
    application = create_app(settings, session_factory)
    application.state.test_sf = session_factory
    try:
        yield application
    finally:
        engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def source_headers(app):
    return {"X-Source-Key": app.state.settings.source_key}


@pytest.fixture
def reviewer_headers(app):
    return {"X-Reviewer-Key": app.state.settings.reviewer_key}


@pytest.fixture
def payload():
    return {
        "external_id": "demo-001",
        "subject": "Invoice request",
        "message": "Please send my invoice.",
    }
