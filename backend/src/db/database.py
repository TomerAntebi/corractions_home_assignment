import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)
DatabaseSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def initialize_database() -> None:
    import db.models  # noqa: F401 - register models with Base metadata

    Base.metadata.create_all(engine)


def create_database_session() -> Generator[Session, None, None]:
    database_session = DatabaseSession()

    try:
        yield database_session
    finally:
        database_session.close()
