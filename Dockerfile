FROM docker.io/library/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANALYTICS_MCP_TRANSPORT=streamable-http \
    HOST=0.0.0.0 \
    PORT=8080 \
    HOME=/tmp

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY analytics_mcp ./analytics_mcp

RUN python -m pip install --no-cache-dir .

USER 65532:65532

EXPOSE 8080

CMD ["analytics-mcp"]
