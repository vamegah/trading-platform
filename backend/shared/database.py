from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.shared.config import settings


def resolve_database_url(database_url: str) -> str:
    """Pin bare ``postgresql://`` URLs to the installed psycopg2 driver.

    SQLAlchemy 2.1 changed the default DBAPI for ``postgresql://`` from psycopg2
    to psycopg (v3). The platform ships psycopg2-binary, so keep the 2.0 behaviour
    explicit. URLs that already name a driver (e.g. ``+psycopg``, ``+asyncpg``)
    and non-PostgreSQL URLs are returned unchanged.
    """
    url = make_url(database_url)
    if url.drivername != "postgresql":
        return database_url
    return url.set(drivername="postgresql+psycopg2").render_as_string(hide_password=False)


def _engine_options(database_url: str) -> dict:
    options: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options.update({"pool_size": 10, "max_overflow": 20})
    return options


engine = create_engine(resolve_database_url(settings.database_url), **_engine_options(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
