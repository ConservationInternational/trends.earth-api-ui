FROM python:3.12-slim

# Install build tools and dependencies
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install poetry first
RUN pip install --no-cache-dir poetry

# Configure Poetry: Disable virtualenv (install in system site-packages)
RUN poetry config virtualenvs.create false

# Copy dependency files for better layer caching
COPY pyproject.toml ./
COPY poetry.lock ./

# Install dependencies only (without installing the project)
RUN poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the project files
COPY README.md ./
COPY trendsearth_ui ./trendsearth_ui
COPY gunicorn.conf.py ./

# Now install the project itself
RUN poetry install --no-interaction --no-ansi

# Expose port 8000 (gunicorn default)
EXPOSE 8000

# Run the app with gunicorn using config file
CMD ["gunicorn", "--config", "gunicorn.conf.py", "trendsearth_ui.app:server"]