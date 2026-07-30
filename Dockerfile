# Use a slim Python image
FROM python:3.13-slim

# Install uv (pinned; avoid :latest so builds are reproducible)
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

WORKDIR /app

# Copy the project files into the container.
# .dockerignore keeps credentials, env files, and VCS metadata out of the
# build context.
COPY . .

# Install the project and its dependencies into the system Python
# environment in the container.
RUN uv pip install --system --no-cache .

# Run as a non-root user.
RUN useradd --create-home --uid 1001 mcp
USER mcp

# Expose port 8080 (default for Cloud Run)
EXPOSE 8080

# Uses the entry point defined in pyproject.toml. The server starts in
# HTTP/OAuth mode when ANALYTICS_MCP_OAUTH_CLIENT_ID and
# ANALYTICS_MCP_OAUTH_CLIENT_SECRET are set.
CMD ["analytics-mcp"]
