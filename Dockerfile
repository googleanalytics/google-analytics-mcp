FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY . .
RUN uv pip install --system .

EXPOSE 8080
CMD ["analytics-mcp"]
