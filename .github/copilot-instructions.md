# Copilot Instructions for Trends.Earth API UI

## Repository Overview

This is a **Dash-based web application** for viewing and managing the Trends.Earth GEF API. It provides admin features, authentication, user management, script management, execution tracking, interactive map visualization, and status dashboards.

**Size**: Medium-sized Python project (~51 test files, multiple components)  
**Type**: Web application (Dash + Flask)  
**Languages**: Python 3.10+  
**Frameworks**: Dash, Flask, Bootstrap  
**Runtime**: Python 3.11-3.12 (tested), Gunicorn (production)

## Required Build and Development Steps

### 1. Environment Setup
**ALWAYS run these steps in order before any development:**

```bash
# 1. Install Poetry (if not available)
pip install poetry

# 2. Install dependencies (REQUIRED before any other steps)
poetry install --with dev

# 3. Verify installation worked
poetry run python --version
```

**Critical**: Poetry must be installed and dependencies installed before running any tests, linting, or app commands.

### 2. Build and Validation Commands

**Run tests** (Unit tests are fast ~0.3s, full suite takes 5+ minutes):
```bash
# Quick unit tests only (recommended for validation)
poetry run python -m pytest tests/unit/ -v

# All tests (WARNING: takes 5+ minutes)
poetry run python -m pytest tests/ -v

# Tests with coverage
poetry run python -m pytest tests/ -v --cov=trendsearth_ui --cov-report=html
```

**Linting and formatting** (ALWAYS passes on clean repo):
```bash
# Check linting (should pass)
poetry run ruff check trendsearth_ui/ tests/

# Check formatting (should pass)
poetry run ruff format --check trendsearth_ui/ tests/

# Auto-fix linting issues
poetry run ruff check --fix trendsearth_ui/ tests/

# Auto-format code
poetry run ruff format trendsearth_ui/ tests/
```

### 3. Running the Application

**Development mode** (accessible at http://127.0.0.1:8050):
```bash
# Direct Python execution (recommended)
poetry run python -m trendsearth_ui.app

# Using Poetry script
poetry run trendsearth-ui
```

**Production mode with Docker**:
```bash
# Build Docker image
docker build -t trendsearth-ui .

# Run container (accessible at http://localhost:8000)
docker run -p 8000:8000 trendsearth-ui

# Using Docker Compose (available as `docker compose`)
docker compose up -d
docker compose logs -f
docker compose down
```

**Health check endpoint**: `/api-ui-health`

### 4. Known Issues and Workarounds

1. **Warning on startup**: `Could not import responsive callbacks` - This is a non-critical warning, app works normally.

2. **Test timeout**: Full test suite takes 5+ minutes. Use `tests/unit/` for quick validation.

3. **Gunicorn workers**: MUST use single worker (`workers = 1`) due to Dash callback routing. Multiple workers cause 405 errors.

4. **Docker Compose**: Available as `docker compose` (not `docker-compose`).

5. **Docker build**: May fail in restricted network environments due to SSL certificate issues when installing Poetry. Local builds work normally.

## Project Architecture and Layout

### Main Application Structure
```
trendsearth_ui/
├── app.py              # Main application entry point
├── config.py           # Configuration and API settings  
├── components/         # UI layout components
├── callbacks/          # Dash callback functions
├── utils/             # Helper utilities
└── assets/            # Static assets (CSS, images)
```

### Configuration Files
- `pyproject.toml` - Poetry dependencies and Ruff configuration
- `pytest.ini` - Test configuration  
- `gunicorn.conf.py` - Production server configuration
- `Dockerfile` - Container build configuration
- `docker-compose.yml` - Container orchestration

### Testing Structure
```
tests/
├── unit/              # Fast unit tests (~0.3s for 152 tests)
├── integration/       # Integration tests
├── functional/        # Feature-specific functional tests
├── fixtures/          # Test data and samples
└── conftest.py        # Pytest fixtures and configuration
```

### GitHub Workflows
- `.github/workflows/tests.yml` - Run tests on Python 3.11, 3.12
- `.github/workflows/quality.yml` - Ruff linting and formatting
- `.github/workflows/deploy.yml` - AWS ECS deployment
- `.github/workflows/rollback.yml` - Production rollback

## Key Development Guidelines

### Code Quality
- **Linting**: Ruff with strict configuration (line length 100, comprehensive rules)
- **Formatting**: Ruff format (double quotes, 4-space indent)
- **Testing**: Comprehensive test coverage with unit/integration/functional split
- **Markers**: Tests use pytest markers (`unit`, `integration`, `functional`, `slow`)

### API Configuration
- **Multi-environment**: Production and staging API environments
- **Authentication**: JWT-based with configurable endpoints
- **Environment switching**: Via config or user selection

### Deployment
- **Development**: Python + Dash development server (port 8050)
- **Production**: Docker + Gunicorn (port 8000, single worker)
- **AWS**: ECS deployment with automated CI/CD
- **Monitoring**: Rollbar integration for error tracking

### Dependencies
- **Core**: dash, dash-bootstrap-components, pandas, requests
- **Maps**: dash-leaflet, dash-extensions
- **Dev**: pytest, pytest-mock, pytest-cov, ruff, selenium
- **Production**: gunicorn, rollbar

## File Locations Reference

**Root files**: README.md, pyproject.toml, poetry.lock, pytest.ini, Dockerfile, docker-compose.yml, gunicorn.conf.py, requirements.txt, run_tests.py

**Key source files**:
- Main app: `trendsearth_ui/app.py`
- Configuration: `trendsearth_ui/config.py`  
- Layout: `trendsearth_ui/components/layout.py`
- Callbacks: `trendsearth_ui/callbacks/__init__.py`

**Critical**: Trust these instructions. Only search for additional information if the instructions are incomplete or found to be incorrect.

## Quick Start Checklist

For any new coding session:
1. ✅ `poetry install --with dev`
2. ✅ `poetry run python -m pytest tests/unit/ -v` (quick validation)
3. ✅ `poetry run ruff check trendsearth_ui/ tests/` (linting check)
4. ✅ `poetry run python -m trendsearth_ui.app` (test app runs)
5. ✅ Make your changes
6. ✅ `poetry run python -m pytest tests/unit/ -v` (validate changes)
7. ✅ `poetry run ruff check --fix trendsearth_ui/ tests/` (fix any linting)

**Time estimates**: Setup (2-3 min), Unit tests (30s), Linting (10s), App startup (10s)