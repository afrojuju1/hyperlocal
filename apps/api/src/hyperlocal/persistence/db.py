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
    from hyperlocal.persistence.models import Base

    Base.metadata.create_all(engine)
    _apply_sql_patches(engine)
    return engine


def build_sessionmaker(database_url: str | None = None):
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _apply_sql_patches(engine) -> None:
    """
    Best-effort schema patching for existing DBs using ordered SQL migration files.
    """
    migrations_dir = Path(__file__).resolve().parents[3] / "sql" / "migrations"
    if not migrations_dir.exists() or not migrations_dir.is_dir():
        return
    migration_files = sorted(
        path for path in migrations_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".sql"
    )
    with engine.begin() as conn:
        for migration_file in migration_files:
            sql = migration_file.read_text(encoding="utf-8")
            if not sql.strip():
                continue
            statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
            for statement in statements:
                conn.execute(text(statement))
