FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

ENV TYPST_INSTALL=/usr/local
RUN curl -fsSL https://install.typst.community/install.sh | sh

COPY backend/pyproject.toml backend/uv.lock /app/
RUN uv sync --frozen --no-dev

COPY backend /app

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
