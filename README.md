# Trends.Earth GEF API Viewer

[![Tests](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/tests.yml/badge.svg?branch=master)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/tests.yml)
[![Code Quality](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/quality.yml/badge.svg?branch=master)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/ConservationInternational/trends.earth-api-ui/branch/master/graph/badge.svg)](https://codecov.io/gh/ConservationInternational/trends.earth-api-ui)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Deploy Status](https://img.shields.io/badge/deployment-EC2-orange.svg)](https://github.com/ConservationInternational/trends.earth-api-ui/actions/workflows/deploy.yml)

A Dash app for viewing and managing the Trends.Earth GEF API, supporting admin features and authentication.

## 🚀 Deployment

This application supports automatic deployment to Amazon EC2 instances using GitHub Actions. See [EC2_DEPLOYMENT_SETUP.md](EC2_DEPLOYMENT_SETUP.md) for detailed setup instructions.

### Available Deployment Workflows:
- **Basic Deployment** (`deploy.yml`) - Simple deployment with process management
- **Production Deployment** (`deploy-production.yml`) - Advanced deployment with systemd, versioning, and rollback capability
- **Rollback** (`rollback.yml`) - Manual rollback to previous deployments

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
git clone <your-repo-url>
cd trends-earth-api-viewer
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

#### Development mode (Direct Python)
```bash
python -m trendsearth_ui.app
```

#### Development mode (Poetry - if Poetry is properly configured)
```bash
poetry run python -m trendsearth_ui.app
```

#### Using Poetry script (if Poetry is properly configured)
```bash
poetry run trendsearth-ui
```

#### Production mode (Docker with Gunicorn)
```bash
# Build the Docker image
docker build -t trendsearth-ui .

# Run the container
docker run -p 8000:8000 trendsearth-ui
```

#### Production mode (Docker Compose)
```bash
# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The app will be available at:
- Development: http://localhost:8050
- Production: http://localhost:8000

Health check endpoint: `/api-ui-health`

## Testing

The project includes a comprehensive test suite with unit, integration, and functional tests.

### Running Tests Locally

#### Install test dependencies
```bash
pip install pytest pytest-mock pytest-cov
```

#### Run all tests
```bash
python -m pytest tests/ -v
```

#### Run tests by category
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only  
python -m pytest tests/integration/ -v

# Functional tests only
python -m pytest tests/functional/ -v
```

#### Run tests with coverage
```bash
python -m pytest tests/ -v --cov=trendsearth_ui --cov-report=html --cov-report=term-missing
```

#### Run specific test file
```bash
python -m pytest tests/unit/test_config.py -v
```

### Test Structure

- **`tests/unit/`** - Unit tests for individual components and utilities
- **`tests/integration/`** - Integration tests for complete app functionality  
- **`tests/functional/`** - Functional tests for specific features
- **`tests/fixtures/`** - Shared test data and samples
- **`conftest.py`** - Pytest configuration and fixtures

### Continuous Integration

Tests and code quality checks are automatically run on GitHub Actions for:
- **Tests**: Python versions 3.9, 3.11, 3.12 on all pushes to `main` and `develop` branches and pull requests
- **Code Quality**: Ruff linting and formatting checks
- **Coverage**: Code coverage is tracked and reported to Codecov

### Code Quality Tools

The project uses Ruff for both linting and code formatting:

```bash
# Lint code with Ruff
ruff check trendsearth_ui/ tests/

# Format code with Ruff
ruff format trendsearth_ui/ tests/

# Fix auto-fixable issues
ruff check --fix trendsearth_ui/ tests/
```

## Configuration

### Application Configuration
The API endpoint and authentication URL are set in `app.py`:

```python
API_BASE_URL = "https://api.trends.earth/api/v1"
AUTH_URL = "https://api.trends.earth/auth"
```

### Gunicorn Configuration
Production deployment uses Gunicorn with the configuration in `gunicorn.conf.py`. 
Key settings:
- 4 worker processes
- 120 second timeout
- Bound to 0.0.0.0:8000
- Request logging enabled

## License

MIT