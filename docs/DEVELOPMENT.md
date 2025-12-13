# Development Guide

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- (Optional) kubectl for Kubernetes deployment

## Local Development

### Running with Docker Compose

The easiest way to run the full application:

```bash
# Start all services
docker-compose up --build

# Start in detached mode
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Access Points

| Service | URL |
|---------|-----|
| Frontend | http://localhost:8080 |
| API Server | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |

## Running Tests

### API Server Tests

```bash
cd api-server

# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_endpoints.py -v
```

### Frontend Tests

```bash
cd frontend

# Install test dependencies
pip install -r requirements-test.txt

# Run tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=term-missing
```

### Running Tests in Docker

If your local Python version is < 3.11:

```bash
# API Server
docker run --rm -v "$(pwd)/api-server:/app" -w /app python:3.11-slim \
  bash -c "pip install -r requirements-test.txt && pytest -v"

# Frontend
docker run --rm -v "$(pwd)/frontend:/app" -w /app python:3.11-slim \
  bash -c "pip install -r requirements-test.txt && pytest -v"
```

## Project Structure

### API Server

```
api-server/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings from environment
│   ├── database.py          # SQLAlchemy async setup
│   ├── models/
│   │   └── aircraft.py      # SQLAlchemy models
│   ├── schemas/
│   │   ├── aircraft.py      # Pydantic schemas
│   │   └── health.py        # Health check schemas
│   ├── services/
│   │   ├── aircraft.py      # Business logic
│   │   └── redis_client.py  # Valkey/Redis client
│   └── routers/
│       ├── aircraft.py      # Aircraft endpoints
│       └── health.py        # Health endpoints
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_endpoints.py    # API endpoint tests
│   ├── test_aircraft_service.py
│   └── test_redis_client.py
├── requirements.txt
├── requirements-test.txt
└── pytest.ini
```

### Frontend

```
frontend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings
│   ├── routers/
│   │   └── pages.py         # Page routes
│   ├── services/
│   │   └── api_client.py    # API server client
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── search.html
│   │   ├── details.html
│   │   ├── health.html
│   │   └── connectivity.html
│   └── static/
│       └── css/
│           └── theme.css    # Light/dark theme
├── tests/
│   ├── conftest.py
│   ├── test_api_client.py
│   └── test_routes.py
├── requirements.txt
├── requirements-test.txt
└── pytest.ini
```

## Environment Variables

### API Server

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_HOST | localhost | PostgreSQL host |
| DATABASE_PORT | 5432 | PostgreSQL port |
| DATABASE_NAME | postgres | Database name |
| DATABASE_USER | postgres | Database user |
| DATABASE_PASSWORD | postgres | Database password |
| REDIS_HOST | localhost | Valkey/Redis host |
| REDIS_PORT | 6379 | Valkey/Redis port |
| LOG_LEVEL | INFO | Logging level |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| API_SERVER_URL | http://localhost:8000 | API server URL |
| LOG_LEVEL | INFO | Logging level |

### ADSB-Sync

| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | localhost | Valkey/Redis host |
| REDIS_PORT | 6379 | Valkey/Redis port |
| POLL_INTERVAL | 1800 | Seconds between polls (30 min) |
| REDIS_TTL | 2100 | Position TTL in seconds (35 min) |
| MAX_BACKOFF | 1800 | Maximum backoff on rate limit |
| LOG_LEVEL | INFO | Logging level |

## Adding New Features

### Adding a New API Endpoint

1. Create/update schema in `api-server/app/schemas/`
2. Add business logic in `api-server/app/services/`
3. Add route in `api-server/app/routers/`
4. Register router in `api-server/app/main.py`
5. Add tests in `api-server/tests/`

### Adding a New Frontend Page

1. Create template in `frontend/app/templates/`
2. Add route in `frontend/app/routers/pages.py`
3. Update API client if needed in `frontend/app/services/api_client.py`
4. Add tests in `frontend/tests/`

## Troubleshooting

### OpenSky API Rate Limiting

If you see HTTP 429 errors in adsb-sync logs:
- The service uses exponential backoff automatically
- Default poll interval is 30 minutes to avoid rate limits
- Consider registering for an OpenSky account for higher limits

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Connect directly
docker-compose exec postgres psql -U postgres
```

### Redis/Valkey Connection Issues

```bash
# Check if Valkey is running
docker-compose ps valkey

# Connect directly
docker-compose exec valkey valkey-cli ping
```
