# Trends.Earth GEF API Viewer

A Dash app for viewing and managing the Trends.Earth GEF API, supporting admin features and authentication.

## Features

- Login/logout with API JWT
- View and edit users and scripts (admin only)
- Browse executions, parameters, results, and logs
- Paging and per-ID search for executions

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

#### Development mode (Poetry)
```bash
poetry run python -m trendsearth_ui.app
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

Health check endpoint: `/health`

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