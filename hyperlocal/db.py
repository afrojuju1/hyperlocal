from __future__ import annotations

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def build_engine(database_url: str | None = None):
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(url, pool_pre_ping=True)


def build_sessionmaker(database_url: str | None = None):
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
