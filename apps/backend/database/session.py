from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from apps.backend.database import connection

_factory = sessionmaker(autocommit=False, autoflush=False)


def SessionLocal(**kwargs) -> Session:  # noqa: N802 - keeps the conventional factory name
    """A session bound to the *current* application engine, resolved at call time rather than import time."""
    return _factory(bind=connection.engine, **kwargs)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
