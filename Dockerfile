# Multi-stage build for Google Analytics MCP Server
# Security: non-root, minimal image, read-only filesystem

# ============================================================
# Stage 1: Build dependencies
# ============================================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

COPY pyproject.toml ./
COPY analytics_mcp/ ./analytics_mcp/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[deploy]"

# ============================================================
# Stage 2: Production image
# ============================================================
FROM python:3.12-slim-bookworm AS production

# Security: non-root user with no login shell
RUN groupadd --gid 1001 mcpuser && \
    useradd --uid 1001 --gid 1001 --shell /usr/sbin/nologin --create-home mcpuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY analytics_mcp/ ./analytics_mcp/

# Application code is immutable
RUN chmod -R 555 /app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8080}/mcp')" || exit 1

USER mcpuser

EXPOSE 8080

CMD ["python", "-m", "analytics_mcp.server_deploy"]
