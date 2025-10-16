import os
from functools import lru_cache
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


Base = declarative_base()


@lru_cache
def _database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://rueo_user:rueo_password@localhost:5432/rueo_db",
    )


def _create_engine() -> Engine:
    return create_engine(
        _database_url(),
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    # Import models for side-effects so SQLAlchemy registers them with the metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
