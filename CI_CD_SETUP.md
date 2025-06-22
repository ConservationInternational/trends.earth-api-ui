# CI/CD and Testing Setup

This document describes the continuous integration and testing setup for the Trends.Earth API UI project.

## GitHub Actions Workflows

### 1. Tests Workflow (`.github/workflows/tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual dispatch

**What it does:**
- Runs tests on Python 3.9, 3.11, and 3.12
- Installs dependencies and the package in development mode
- Runs unit, integration, and functional tests separately
- Generates code coverage reports
- Uploads coverage to Codecov (for Python 3.11 only)

**Commands:**
```bash
# Unit tests with coverage
python -m pytest tests/unit/ -v --cov=trendsearth_ui --cov-report=xml --cov-report=term-missing

# Integration tests
python -m pytest tests/integration/ -v

# Functional tests  
python -m pytest tests/functional/ -v
```

### 2. Code Quality Workflow (`.github/workflows/quality.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**What it does:**
- Checks code formatting and linting with Ruff

**Commands:**
```bash
# Lint code
ruff check trendsearth_ui/ tests/

# Check formatting
ruff format --check trendsearth_ui/ tests/
```

## Badges

The README.md includes status badges for:
- **Tests**: Shows if the test suite is passing
- **Code Quality**: Shows if code quality checks are passing
- **Coverage**: Shows code coverage percentage from Codecov

```markdown
[![Tests](https://github.com/azvoleff/trends.earth-api-ui/actions/workflows/tests.yml/badge.svg)](https://github.com/azvoleff/trends.earth-api-ui/actions/workflows/tests.yml)
[![Code Quality](https://github.com/azvoleff/trends.earth-api-ui/actions/workflows/quality.yml/badge.svg)](https://github.com/azvoleff/trends.earth-api-ui/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/azvoleff/trends.earth-api-ui/branch/main/graph/badge.svg)](https://codecov.io/gh/azvoleff/trends.earth-api-ui)
```

## Configuration Files

### Testing Configuration

1. **`pytest.ini`** - Pytest configuration (legacy format, maintained for compatibility)
2. **`pyproject.toml`** - Modern Python project configuration including:
   - Poetry dependencies (including dev dependencies)
   - Ruff configuration for linting and formatting
   - pytest configuration
   - Build system configuration

### Code Quality Configuration

**Ruff configuration** (in `pyproject.toml`):
- Target Python version: 3.9+
- Line length: 100
- Enabled rule sets: pycodestyle, pyflakes, isort, flake8-bugbear, flake8-comprehensions, pyupgrade
- Custom ignores and per-file ignores
- Import sorting configuration
- Formatting configuration

## Package Installation

The project can be installed in multiple ways:

### Development Installation
```bash
# Using pip (recommended for CI)
pip install -e .

# Using Poetry (recommended for local development)
poetry install --with dev
```

### Setup Files

1. **`setup.py`** - Traditional setuptools configuration for pip installation
2. **`pyproject.toml`** - Modern Poetry/PEP 518 configuration
3. **`requirements.txt`** - Runtime dependencies for pip

## GitHub Templates

### Issue Templates
- **Bug Report** (`.github/ISSUE_TEMPLATE/bug_report.md`)
- **Feature Request** (`.github/ISSUE_TEMPLATE/feature_request.md`)

### Pull Request Template
- **PR Template** (`.github/pull_request_template.md`)
- Includes checklists for testing, code quality, and documentation

## Local Development Workflow

### Before Committing
```bash
# Run all tests
python -m pytest tests/ -v

# Check and fix code quality
ruff check --fix trendsearth_ui/ tests/
ruff format trendsearth_ui/ tests/

# Run tests with coverage
python -m pytest tests/ -v --cov=trendsearth_ui --cov-report=html
```

### IDE Integration

The Ruff configuration in `pyproject.toml` supports integration with popular IDEs:
- **VS Code**: Ruff extension will use the configuration automatically
- **PyCharm**: Can import settings from `pyproject.toml`

## Coverage Reporting

- **Local**: HTML coverage reports generated in `htmlcov/` directory
- **CI**: XML coverage reports uploaded to Codecov
- **Badge**: Coverage percentage displayed in README

## Workflow Optimization

- **Caching**: Pip dependencies are cached to speed up workflow runs
- **Matrix Strategy**: Tests run on multiple Python versions in parallel
- **Conditional Steps**: Coverage upload only happens for Python 3.11 to avoid duplicates
- **Separate Workflows**: Tests and code quality run separately for better failure isolation

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure package is installed with `pip install -e .`
2. **Test Discovery**: Check that test files start with `test_` and are in the `tests/` directory
3. **Code Quality Failures**: Run tools locally first to fix issues before pushing:
   ```bash
   ruff check --fix trendsearth_ui/ tests/
   ruff format trendsearth_ui/ tests/
   ```
4. **Coverage Issues**: Ensure tests are actually importing and using the code being tested

### Debugging CI Failures

1. Check the specific step that failed in the GitHub Actions logs
2. Run the same commands locally to reproduce the issue
3. Check if dependencies need to be updated
4. Verify that file paths and imports are correct
