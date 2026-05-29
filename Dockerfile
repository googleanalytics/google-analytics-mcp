# Use a slim Python image
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Copy the project files into the container
COPY . .

# Install the project and its dependencies
RUN uv pip install --system .

# Expose port 8080 (default for Cloud Run)
EXPOSE 8080

# Define the command to run the server
CMD ["analytics-mcp"]
