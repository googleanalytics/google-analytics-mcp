FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_NO_DEV=1

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --all-extras --no-dev --no-install-project

COPY . .

RUN uv sync --all-extras --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
