# Planespotter Architecture

## Overview

Planespotter is a microservices application demonstrating modern cloud-native patterns. It tracks aircraft using real-time ADS-B data from the OpenSky Network.

## System Architecture

```
                                    ┌─────────────────┐
                                    │   OpenSky API   │
                                    │  (External)     │
                                    └────────┬────────┘
                                             │ HTTPS/443
                                             │ (every 30 min)
                                             ▼
┌─────────┐      ┌──────────┐      ┌─────────────────┐      ┌─────────────┐
│ Browser │──────│ Frontend │──────│   API Server    │──────│ PostgreSQL  │
│         │ 8080 │ (FastAPI)│ 8000 │   (FastAPI)     │ 5432 │             │
└─────────┘      └──────────┘      └────────┬────────┘      └─────────────┘
                                            │
                                            │ 6379
                                            ▼
                                   ┌─────────────────┐
                                   │     Valkey      │◄────── ADSB-Sync
                                   │  (Redis Cache)  │        (Python)
                                   └─────────────────┘
```

## Services

### Frontend
- **Technology**: FastAPI + Jinja2 + Bootstrap 5
- **Port**: 8080
- **Purpose**: Server-side rendered web interface
- **Features**:
  - Aircraft search with filters
  - Aircraft detail pages with live position
  - Health dashboard
  - Network connectivity visualization
  - Light/dark theme support

### API Server
- **Technology**: FastAPI + SQLAlchemy 2.0 (async)
- **Port**: 8000
- **Purpose**: REST API for aircraft data
- **Endpoints**:
  - `GET /api/v1/aircraft` - Search with pagination
  - `GET /api/v1/aircraft/{icao24}` - Aircraft details + live position
  - `GET /api/v1/health` - Health dashboard data
  - `GET /api/v1/connectivity` - Network connectivity matrix
  - `GET /health` - Liveness probe
  - `GET /health/ready` - Readiness probe

### ADSB-Sync
- **Technology**: Python asyncio + httpx
- **Purpose**: Background service polling OpenSky Network
- **Behavior**:
  - Polls OpenSky API every 30 minutes (configurable)
  - Stores aircraft positions in Valkey with 35-minute TTL
  - Implements exponential backoff on rate limiting (HTTP 429)
  - Anonymous API access (rate-limited)

### Database (PostgreSQL)
- **Technology**: PostgreSQL 15
- **Port**: 5432
- **Purpose**: Persistent aircraft metadata storage
- **Data**: ~500,000 aircraft records from OpenSky dataset
- **Schema**: Single `aircraft_metadata` table with registration, manufacturer, model, operator, etc.

### Cache (Valkey)
- **Technology**: Valkey 8 (Redis-compatible)
- **Port**: 6379
- **Purpose**: Real-time aircraft position cache
- **Data Structure**: Key-value with `aircraft:{icao24}` keys
- **TTL**: 35 minutes (outlasts poll interval)

## Data Flow

### Aircraft Search
1. User enters search criteria in Frontend
2. Frontend calls API Server `/api/v1/aircraft`
3. API Server queries PostgreSQL for matching aircraft
4. API Server checks Valkey for each aircraft's airborne status
5. Results returned with `is_airborne` flag

### Aircraft Detail with Position
1. User clicks aircraft in search results
2. Frontend calls API Server `/api/v1/aircraft/{icao24}`
3. API Server fetches metadata from PostgreSQL
4. API Server fetches live position from Valkey
5. Combined response includes position if aircraft is tracked

### Position Updates
1. ADSB-Sync polls OpenSky Network API
2. Receives state vectors for all tracked aircraft
3. Stores each position in Valkey with TTL
4. Old positions expire automatically

## Network Requirements

| Source | Destination | Port | Protocol | Required |
|--------|-------------|------|----------|----------|
| Browser | Frontend | 8080 | HTTP | Yes |
| Frontend | API Server | 8000 | HTTP | Yes |
| API Server | PostgreSQL | 5432 | TCP | Yes |
| API Server | Valkey | 6379 | TCP | Yes |
| ADSB-Sync | Valkey | 6379 | TCP | Yes |
| ADSB-Sync | opensky-network.org | 443 | HTTPS | Yes |

## Deployment Options

### Docker Compose (Development)
```bash
docker-compose up --build
```

### Kubernetes (Production)
```bash
kubectl apply -k kubernetes/
```

The Kubernetes deployment uses Kustomize and includes:
- Namespace isolation (`planespotter`)
- ConfigMaps for configuration
- Services for internal communication
- Deployments with health checks

## Security Considerations

- No authentication (demo application)
- All services communicate over internal network
- External access only through Frontend (8080)
- OpenSky API uses anonymous access (rate-limited)
- Database credentials via environment variables

## Monitoring

### Health Endpoints
- `/health` - Simple liveness (returns `{"status": "ok"}`)
- `/health/ready` - Checks database and cache connectivity
- `/api/v1/health` - Detailed service health with latencies

### Connectivity Matrix
The `/api/v1/connectivity` endpoint tests TCP connectivity to:
- PostgreSQL (5432)
- Valkey (6379)
- OpenSky Network (443)

This is useful for demonstrating network policies and micro-segmentation.
