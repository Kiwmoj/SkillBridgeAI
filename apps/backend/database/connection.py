from sqlalchemy import Engine, create_engine, event

from apps.backend.core.config import settings

DATABASE_URL = settings.database_url


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False, "timeout": 20})

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys = ON")

        return engine
    # Recycle pooled connections before managed PostgreSQL services drop idle ones.
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800)


engine = make_engine(DATABASE_URL)
