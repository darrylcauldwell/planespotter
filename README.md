# Planespotter

A microservices demo application for tracking aircraft using real-time ADS-B data from OpenSky Network.

## Architecture

```
Browser → Frontend (8080) → API Server (8000) → PostgreSQL (5432)
                                             → Valkey (6379) ← ADSB-Sync → OpenSky API
```

### Services

| Service | Technology | Description |
|---------|------------|-------------|
| **Frontend** | FastAPI + Jinja2 + Bootstrap 5 | Web interface for searching and viewing aircraft |
| **API Server** | FastAPI + SQLAlchemy 2.0 | REST API for aircraft data |
| **ADSB-Sync** | Python asyncio + httpx | Polls OpenSky Network for live positions |
| **Database** | PostgreSQL 15 | Aircraft metadata from OpenSky dataset |
| **Cache** | Valkey 8 | Real-time aircraft position cache |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- (Optional) Kubernetes cluster with kubectl

### Local Development with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:8080
# API Docs: http://localhost:8000/docs
```

### Kubernetes Deployment

```bash
# Build container images
docker build -t planespotter-db:latest ./db-install
docker build -t planespotter-api:latest ./api-server
docker build -t planespotter-frontend:latest ./frontend
docker build -t planespotter-adsb-sync:latest ./adsb-sync

# Deploy with Kustomize
kubectl apply -k kubernetes/

# Check deployment status
kubectl get pods -n planespotter
```

## Features

- **Aircraft Search**: Search by registration, ICAO24, manufacturer, model, operator, or owner
- **Live Position Tracking**: View real-time position data for airborne aircraft
- **Health Dashboard**: Monitor the status of all microservices
- **Auto-generated API Docs**: Interactive Swagger UI at `/docs`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/aircraft` | Search aircraft with pagination |
| GET | `/api/v1/aircraft/{icao24}` | Get aircraft details with live position |
| GET | `/health` | Liveness probe |
| GET | `/health/ready` | Readiness probe |
| GET | `/api/v1/health` | Detailed health status |

## Configuration

### Environment Variables

**API Server:**
| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_HOST | localhost | PostgreSQL host |
| DATABASE_PORT | 5432 | PostgreSQL port |
| DATABASE_NAME | postgres | Database name |
| DATABASE_USER | postgres | Database user |
| DATABASE_PASSWORD | postgres | Database password |
| REDIS_HOST | localhost | Redis host |
| REDIS_PORT | 6379 | Redis port |

**Frontend:**
| Variable | Default | Description |
|----------|---------|-------------|
| API_SERVER_URL | http://localhost:8000 | API server URL |

**ADSB-Sync:**
| Variable | Default | Description |
|----------|---------|-------------|
| REDIS_HOST | localhost | Redis host |
| REDIS_PORT | 6379 | Redis port |
| POLL_INTERVAL | 30 | Seconds between OpenSky polls |
| REDIS_TTL | 60 | Position data TTL in seconds |

## Data Source

Aircraft metadata is sourced from [OpenSky Network](https://opensky-network.org/):
- Dataset: [Aircraft Database CSV](https://opensky-network.org/datasets/metadata/)
- Live positions: [OpenSky Network API](https://opensky-network.org/apidoc/)

The application uses anonymous API access which has rate limits. For production use, consider registering for an OpenSky account.

## Project Structure

```
planespotter/
├── .github/workflows/   # GitHub Actions CI/CD
├── api-server/          # FastAPI REST API
│   └── tests/           # pytest test suite
├── frontend/            # FastAPI + Jinja2 web UI
│   └── tests/           # pytest test suite
├── adsb-sync/           # OpenSky → Redis sync service
├── db-install/          # PostgreSQL with data import
├── kubernetes/          # Kubernetes Kustomize manifests
├── docs/                # Architecture documentation
├── docker-compose.yaml  # Local development setup
└── README.md
```

## Testing

```bash
# Run API server tests
cd api-server
pip install -r requirements-test.txt
pytest -v --cov=app

# Run frontend tests
cd frontend
pip install -r requirements-test.txt
pytest -v --cov=app
```

## CI/CD

The project uses GitHub Actions for continuous integration:
- **Tests**: Run on every push and pull request
- **Build**: Container images built and pushed to GitHub Container Registry
- **Registry**: `ghcr.io/<owner>/planespotter/<service>`

## Communication Matrix

| Source | Destination | Port | Purpose |
|--------|-------------|------|---------|
| Browser | Frontend | TCP/8080 | Web interface |
| Frontend | API Server | TCP/8000 | REST API calls |
| API Server | PostgreSQL | TCP/5432 | Aircraft metadata |
| API Server | Valkey | TCP/6379 | Live positions |
| ADSB-Sync | Valkey | TCP/6379 | Cache updates |
| ADSB-Sync | OpenSky API | TCP/443 | Fetch positions |

## License

Copyright 2018 Yves Fauser. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
