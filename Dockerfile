FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.1 /uv /uvx /bin/

COPY . /app
WORKDIR /app

RUN ls -la > ls.txt

RUN uv sync --locked
CMD ["uv", "run", "analytics-mcp"]
