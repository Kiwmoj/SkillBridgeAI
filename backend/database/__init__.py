from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import settings

DATABASE_URL = settings.database_url


def make_engine(url: str):
    sqlite = url.startswith("sqlite")
    if sqlite:
        result = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False, "timeout": 20})

        @event.listens_for(result, "connect")
        def enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys = ON")
    else:
        # Recycle pooled connections before managed PostgreSQL services drop idle ones.
        result = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10,
                               pool_timeout=30, pool_recycle=1800)
    return result


engine = make_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
