"""Shared pytest fixtures: an isolated, migrated SQLite database and a FastAPI test client per test."""
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from apps.backend.api.middleware import rate_limiter
from apps.backend.core import config
from apps.backend.database import connection, make_engine
from apps.backend.database.session import get_db
from apps.backend.main import app

ROOT = Path(__file__).resolve().parents[1]


def migrate(engine: Engine) -> None:
    alembic_config = Config(str(ROOT / "alembic.ini"))
    with engine.begin() as db:
        alembic_config.attributes["connection"] = db
        command.upgrade(alembic_config, "head")


@pytest.fixture
def engine(tmp_path, monkeypatch) -> Iterator[Engine]:
    """A migrated per-test SQLite engine installed as the application engine."""
    test_engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    migrate(test_engine)
    monkeypatch.setattr(connection, "engine", test_engine)
    monkeypatch.setattr(config, "settings", replace(config.settings, upload_dir=tmp_path / "uploads"))
    rate_limiter.reset()
    try:
        yield test_engine
    finally:
        test_engine.dispose()


@pytest.fixture
def client(engine) -> Iterator[TestClient]:
    def session():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
