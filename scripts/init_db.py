from __future__ import annotations

import os

from hyperlocal.db import build_engine
from hyperlocal.models import Base


def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set")
    engine = build_engine(database_url)
    Base.metadata.create_all(engine)
    print("Database tables created.")


if __name__ == "__main__":
    main()
