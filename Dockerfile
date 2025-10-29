# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Set the working directory in the container.
WORKDIR /app

# Copy the dependency file to the working directory.
COPY pyproject.toml .

# Install any dependencies.
RUN pip install --no-cache-dir -e .

# Copy the rest of the working directory contents into the container.
COPY . .

# Set the port that the container will listen on.
# This is the default port for Cloud Run.
ENV PORT=8080
ENV HOST=0.0.0.0

# Run the application.
CMD ["analytics-mcp"]
