.PHONY: help setup install install-dev test test-unit test-integration test-all coverage clean format lint type-check docker-up docker-down docker-clean pre-commit build

# Default target
help:
	@echo "Universal Repository Cloner - Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup          - Create venv and install dependencies"
	@echo "  make install        - Install core dependencies only"
	@echo "  make install-dev    - Install core + development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests (unit + integration)"
	@echo "  make test-unit      - Run unit tests only (fast)"
	@echo "  make test-integration - Run integration tests (requires Docker)"
	@echo "  make coverage       - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format         - Format code with black and isort"
	@echo "  make lint           - Run linters (flake8, pylint)"
	@echo "  make type-check     - Run type checking with mypy"
	@echo "  make pre-commit     - Install pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up      - Start test infrastructure"
	@echo "  make docker-down    - Stop test infrastructure"
	@echo "  make docker-clean   - Stop and remove all volumes"
	@echo ""
	@echo "Build:"
	@echo "  make build          - Build distribution package"
	@echo "  make clean          - Remove build artifacts and cache"

# Setup virtual environment and install dependencies
setup:
	python3 -m venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"
	@echo "Then run: make install-dev"

# Install core dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Install development dependencies
install-dev:
	pip install --upgrade pip
	pip install -r requirements-dev.txt

# Run all tests
test: test-unit test-integration

# Run unit tests only (fast, no Docker)
test-unit:
	pytest tests/unit/ -v -m unit

# Run integration tests (requires Docker)
test-integration:
	@echo "Starting Docker test infrastructure..."
	docker-compose -f docker-compose.test.yml up -d localstack azurite fake-gcs-server minio
	@echo "Waiting for services to be ready..."
	sleep 15
	pytest tests/integration/ -v -m integration
	@echo "Stopping Docker test infrastructure..."
	docker-compose -f docker-compose.test.yml down

# Run all tests with coverage
coverage:
	pytest tests/ -v --cov=src/repo_cloner --cov-report=term-missing --cov-report=html

# Format code
format:
	black --line-length=100 src/ tests/
	isort --profile black --line-length=100 src/ tests/

# Run linters
lint:
	flake8 src/ tests/ --max-line-length=100 --extend-ignore=E203,W503
	pylint src/repo_cloner/

# Type checking
type-check:
	mypy src/ --ignore-missing-imports --no-strict-optional

# Install pre-commit hooks
pre-commit:
	pre-commit install
	@echo "Pre-commit hooks installed"

# Start Docker test infrastructure
docker-up:
	docker-compose -f docker-compose.test.yml up -d
	@echo "Test infrastructure starting. Wait ~15 seconds for services to be ready."
	@echo "Services: LocalStack (S3), Azurite (Azure), GCS, MinIO, GitLab, Gitea"

# Stop Docker test infrastructure
docker-down:
	docker-compose -f docker-compose.test.yml down

# Clean Docker (stop and remove volumes)
docker-clean:
	docker-compose -f docker-compose.test.yml down -v
	@echo "All test infrastructure stopped and volumes removed"

# Build distribution package
build:
	python -m build

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	@echo "Clean complete"
