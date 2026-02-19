from __future__ import annotations

import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def build_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(url, pool_pre_ping=True)


def init_db(database_url: str | None = None):
    engine = build_engine(database_url)
    from hyperlocal.models import Base

    Base.metadata.create_all(engine)
    _apply_sql_patches(engine)
    return engine


def build_sessionmaker(database_url: str | None = None):
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _apply_sql_patches(engine) -> None:
    """
    Best-effort schema patching for existing DBs that predate the canonical
    creative-runs pipeline columns.
    """
    migration_file = (
        Path(__file__).resolve().parents[1]
        / "sql"
        / "migrations"
        / "0002_creative_runs_v1.sql"
    )
    if not migration_file.exists():
        return
    sql = migration_file.read_text(encoding="utf-8")
    if not sql.strip():
        return
    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
