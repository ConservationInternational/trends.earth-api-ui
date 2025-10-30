# Trends.Earth GEF API Viewer

[![Tests](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/tests.yml)
[![Code Quality](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/quality.yml/badge.svg?branch=master)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/ConservationInternational/trends.earth-api-ui/branch/master/graph/badge.svg)](https://codecov.io/gh/ConservationInternational/trends.earth-api-ui)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Deploy Status](https://img.shields.io/badge/deployment-EC2_Docker_Swarm-blue.svg)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/deploy-production.yml)

A Dash app for viewing and managing the Trends.Earth GEF API, supporting admin features and authentication.

## 🚀 Deployment

This application supports automatic deployment to EC2 instances using Docker Swarm and GitHub Actions.

### Available Deployment Workflows:
- **Production Deployment** (`deploy-production.yml`) - Production deployment to EC2 with Docker Swarm, health checks, and Rollbar integration
- **Staging Deployment** (`deploy-staging.yml`) - Staging deployment to EC2 for testing and validation  
- **Production Rollback** (`rollback-production.yml`) - Manual rollback to previous deployments or specific commits

### Deployment Architecture:
- **Platform**: EC2 instances with Docker Swarm
- **SSH Deployment**: Secure deployment via SSH using GitHub Actions
- **Health Monitoring**: Automated health checks and integration testing
- **Security**: Dynamic security group management for GitHub Actions runners
- **Registry**: Local Docker registry with build-on-server approach

### Error Tracking
The application includes integrated Rollbar error tracking for production monitoring and debugging.

### Setup Instructions
For detailed deployment setup instructions, see:
- [Deployment README](docs/deployment/README.md) - Overview and GitHub secrets configuration
- [AWS Infrastructure Setup](docs/deployment/aws-infrastructure-setup.md) - EC2 and AWS resource setup
- [Setup Script](scripts/setup-github-secrets.sh) - Automated GitHub secrets configuration

## Features

- Login/logout with API JWT
- View and edit users and scripts (admin only)
- Browse executions, parameters, results, and logs
- Paging and per-ID search for executions
- **Map Visualization** - View execution areas on an interactive map:
  - Click "Show Map" buttons in the Executions table to display processing areas
  - Automatically parses GeoJSON data from execution parameters
  - Interactive Leaflet map with area boundaries highlighted
  - Automatically centers and zooms to show the processing area
- **Status Dashboard** (admin only) - View system status with:
  - Text summary from the most recent status log entry
  - Interactive charts showing execution counts by status over time
  - Three time period views: Last Hour, Last 24 Hours, Last Week
  - Auto-refresh every 60 seconds
- **Edit Functionality** (admin only) - Edit users and scripts directly from the tables:
  - Click "Edit" buttons in Users table to modify user details (name, institution, country, role)
  - Click "Edit" buttons in Scripts table to modify script details (name, description, publication status)
  - Modal dialogs with form validation and error handling
  - Automatic table refresh after successful edits
  - Correctly identifies the selected user/script even when the table is sorted or filtered

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ConservationInternational/trends.earth-api-ui.git
cd trends.earth-api-ui
```

### 2. Install Poetry

If you don't have poetry:

```bash
pip install poetry
```

### 3. Install dependencies

```bash
poetry install
```

### 4. Run the app

#### Development mode (Recommended)
```bash
poetry run python -m trendsearth_ui.app
```

#### Using Poetry script
```bash
poetry run trendsearth-api-ui
```

#### Production mode (Docker with Gunicorn)
```bash
# Build the Docker image
docker build -t trendsearth-api-ui .

# Run the container
docker run -p 8000:8000 trendsearth-api-ui
```

#### Production mode (Docker Compose)
```bash
# Run with docker compose
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

The app will be available at:
- Development: http://localhost:8050
- Production: http://localhost:8000

Health check endpoint: `/api-ui-health`

## Testing

The project includes a comprehensive test suite with unit, integration, and functional tests.

### Running Tests Locally

#### Install test dependencies (if not using Poetry)
```bash
pip install pytest pytest-mock pytest-cov
```

#### Run all tests
```bash
poetry run python -m pytest tests/ -v
```

#### Run tests by category
```bash
# Unit tests only
poetry run python -m pytest tests/unit/ -v

# Integration tests only  
poetry run python -m pytest tests/integration/ -v

# Functional tests only
poetry run python -m pytest tests/functional/ -v

# Playwright end-to-end tests only
poetry run python -m pytest tests/playwright/ -v --browser chromium
```

#### Run tests with coverage
```bash
poetry run python -m pytest tests/ -v --cov=trendsearth_ui --cov-report=html --cov-report=term-missing
```

#### Run specific test file
```bash
poetry run python -m pytest tests/unit/test_config.py -v
```

### Playwright End-to-End Testing

The project includes Playwright tests for comprehensive end-to-end testing of the web application.

#### Setup Playwright
```bash
# Install playwright browsers (required for local testing)
poetry run playwright install

# Or install specific browsers
poetry run playwright install chromium
```

#### Run Playwright Tests
```bash
# Run all playwright tests
poetry run python -m pytest tests/playwright/ -v --browser chromium

# Run with multiple browsers
poetry run python -m pytest tests/playwright/ -v --browser chromium --browser firefox

# Run with headed browser (see the browser)
poetry run python -m pytest tests/playwright/ -v --browser chromium --headed

# Generate test report
poetry run python -m pytest tests/playwright/ -v --browser chromium --html=playwright-report.html
```

#### Playwright Test Categories
- **App Core Tests**: Basic application loading, navigation, and error handling
- **Authentication Tests**: Login/logout flows and session management
- **Dashboard Tests**: Tab navigation and dashboard functionality

### Test Structure

- **`tests/unit/`** - Unit tests for individual components and utilities
- **`tests/integration/`** - Integration tests for complete app functionality  
- **`tests/functional/`** - Functional tests for specific features
- **`tests/playwright/`** - End-to-end tests using Playwright for browser automation
- **`tests/fixtures/`** - Shared test data and samples
- **`conftest.py`** - Pytest configuration and fixtures

### Continuous Integration

Tests and code quality checks are automatically run on GitHub Actions for:
- **Tests**: Python versions 3.11, 3.12 on all pushes to `master` and `develop` branches and pull requests
- **Playwright Tests**: End-to-end testing with Chromium browser automation
- **Code Quality**: Ruff linting and formatting checks
- **Coverage**: Code coverage is tracked and reported to Codecov

### Code Quality Tools

The project uses Ruff for both linting and code formatting:

```bash
# Lint code with Ruff
poetry run ruff check trendsearth_ui/ tests/

# Format code with Ruff
poetry run ruff format trendsearth_ui/ tests/

# Fix auto-fixable issues
poetry run ruff check --fix trendsearth_ui/ tests/
```

## Configuration

### Application Configuration
The API endpoints are configured in `trendsearth_ui/config.py` with support for multiple environments:

```python
API_ENVIRONMENTS = {
    "production": {
        "base": "https://api.trends.earth/api/v1",
        "auth": "https://api.trends.earth/auth",
        "display_name": "Production (api.trends.earth)",
    },
    "staging": {
        "base": "https://api-staging.trends.earth/api/v1", 
        "auth": "https://api-staging.trends.earth/auth",
        "display_name": "Staging (api-staging.trends.earth)",
    },
}
```

Users can switch between environments via the UI, with production as the default.

### Gunicorn Configuration
Production deployment uses Gunicorn with the configuration in `gunicorn.conf.py`. 
Key settings:
- Single worker process (required for Dash callback routing)
- 120 second timeout
- Bound to 0.0.0.0:8000
- Request logging enabled

## License

MIT