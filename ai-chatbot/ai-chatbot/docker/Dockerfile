FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

FROM base AS development

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python

COPY pyproject.toml uv.lock* ./


RUN uv venv /opt/venv --python /usr/local/bin/python

COPY alembic.ini ./alembic.ini

COPY manage.py ./manage.py

COPY . .

ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

RUN uv pip install .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS production

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python

COPY pyproject.toml uv.lock* ./
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY manage.py ./manage.py

RUN uv venv /opt/venv --python /usr/local/bin/python

ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

RUN uv pip install .

RUN mkdir -p /app/logs && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
