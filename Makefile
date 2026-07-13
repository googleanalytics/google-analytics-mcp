VERSION  ?= $(shell python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
PLATFORM ?= linux/amd64
IMAGE    ?= analytics-mcp
PORT     ?= 8080

# ==============================================================================
# Local Development
# ==============================================================================

.PHONY: install
install:
	pip install --editable ".[dev,deploy]"

.PHONY: lint
lint:
	black --check analytics_mcp/ tests/

.PHONY: format
format:
	black analytics_mcp/ tests/

.PHONY: test
test:
	nox -s test

.PHONY: clean
clean:
	-rm -rf build/ dist/ *.egg-info .nox __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ==============================================================================
# Docker
# ==============================================================================

.PHONY: package
package:
	docker build \
		--platform=$(PLATFORM) \
		--tag $(IMAGE):$(VERSION) \
		--tag $(IMAGE):latest \
		.

.PHONY: docker-run
docker-run:
	docker run --rm \
		--platform=$(PLATFORM) \
		--env-file .env \
		-v $${GOOGLE_APPLICATION_CREDENTIALS_HOST_PATH:-./secrets/sa-key.json}:/secrets/sa-key.json:ro \
		-p $(PORT):8080 \
		--read-only \
		--tmpfs /tmp:noexec,nosuid,size=64m \
		--security-opt no-new-privileges:true \
		$(IMAGE):$(VERSION)

.PHONY: docker-up
docker-up:
	docker compose up --build -d

.PHONY: docker-down
docker-down:
	docker compose down

.PHONY: docker-logs
docker-logs:
	docker compose logs -f analytics-mcp

# ==============================================================================
# CI — Run in Docker (no local Python needed)
# ==============================================================================

.PHONY: lint-in-docker
lint-in-docker:
	$(MAKE) COMMAND="black --check analytics_mcp/ tests/" _run_in_docker

.PHONY: test-in-docker
test-in-docker:
	$(MAKE) COMMAND="nox -s test" _run_in_docker

.PHONY: _run_in_docker
_run_in_docker:
	docker run --rm \
		--platform=$(PLATFORM) \
		--volume $(CURDIR):/workspace \
		--workdir /workspace \
		$(EXTRA_DOCKER_ARGS) \
		python:3.12-slim-bookworm \
		bash -c "pip install --quiet '.[dev,deploy]' && $(COMMAND)"

# ==============================================================================
# Helpers
# ==============================================================================

.PHONY: env
env:
	@test -f .env || cp .env.example .env
	@echo ".env file ready — edit with your credentials"

.PHONY: help
help:
	@echo "Local Development:"
	@echo "  make install          Install editable with dev + deploy deps"
	@echo "  make lint             Check formatting with black"
	@echo "  make format           Auto-format with black"
	@echo "  make test             Run tests via nox"
	@echo "  make clean            Remove build artifacts"
	@echo ""
	@echo "Docker:"
	@echo "  make package          Build production Docker image"
	@echo "  make docker-run       Run container standalone"
	@echo "  make docker-up        Start via docker compose"
	@echo "  make docker-down      Stop docker compose"
	@echo "  make docker-logs      Tail compose logs"
	@echo ""
	@echo "CI (in Docker):"
	@echo "  make lint-in-docker   Lint without local Python"
	@echo "  make test-in-docker   Test without local Python"
	@echo ""
	@echo "Helpers:"
	@echo "  make env              Create .env from .env.example"
