import asyncio
import time
import socket
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.redis_client import redis_client
from app.schemas.health import ServiceHealth, HealthCheckResponse
from app.config import settings
from app.metrics import SERVICE_UP, SERVICE_LATENCY

router = APIRouter(tags=["health"])

def get_service_checks():
    checks = [
        # Core app services (critical=True)
        {"name": "database", "host": settings.database_host, "port": settings.database_port, "description": "PostgreSQL", "critical": True, "check": "database"},
        {"name": "valkey", "host": settings.redis_host, "port": settings.redis_port, "description": "Cache", "critical": True, "check": "valkey"},
        {"name": "api-server", "host": "localhost", "port": 8000, "description": "FastAPI backend", "critical": True, "check": "tcp"},
        {"name": "frontend", "host": settings.frontend_host, "port": 8080, "description": "Web UI", "critical": True, "check": "tcp"},
        {"name": "adsb-sync", "host": settings.adsb_sync_host, "port": settings.adsb_sync_port, "description": "ADS-B poller", "critical": True, "check": "tcp"},
        # Observability stack (critical=False)
        {"name": "prometheus", "host": "prometheus", "port": 9090, "description": "Metrics store", "critical": False, "check": "tcp"},
        {"name": "grafana", "host": "grafana", "port": 3000, "description": "Dashboards", "critical": False, "check": "tcp"},
        {"name": "loki", "host": "loki", "port": 3100, "description": "Log aggregator", "critical": False, "check": "tcp"},
        {"name": "promtail", "host": "promtail", "port": 9080, "description": "Log shipper", "critical": False, "check": "tcp"},
        {"name": "cadvisor", "host": "cadvisor", "port": 8080, "description": "Container metrics", "critical": False, "check": "tcp"},
    ]
    if settings.postgres_exporter_host:
        checks.append({"name": "postgres-exporter", "host": settings.postgres_exporter_host, "port": 9187, "description": "DB metrics", "critical": False, "check": "tcp"})
    if settings.valkey_exporter_host:
        checks.append({"name": "valkey-exporter", "host": settings.valkey_exporter_host, "port": 9121, "description": "Cache metrics", "critical": False, "check": "tcp"})
    return checks


@router.get("/health")
async def liveness():
    """Liveness probe - simple check that the app is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe - checks if dependencies are available."""
    db_ok = await check_database()
    valkey_ok = await redis_client.ping()

    if db_ok and valkey_ok:
        return {"status": "ready"}
    return {"status": "not ready", "database": db_ok, "valkey": valkey_ok}


@router.get("/api/v1/health", response_model=HealthCheckResponse)
async def health_dashboard():
    """Detailed health check for dashboard display."""
    services = []

    # --- Deep checks for database and valkey ---
    db_start = time.time()
    db_ok = await check_database()
    db_duration = time.time() - db_start
    SERVICE_UP.labels(service="database").set(1 if db_ok else 0)
    SERVICE_LATENCY.labels(service="database").observe(db_duration)
    services.append(
        ServiceHealth(
            name="database",
            status="healthy" if db_ok else "unhealthy",
            latency_ms=round(db_duration * 1000, 2),
            message="PostgreSQL connected" if db_ok else "Connection failed",
            description="PostgreSQL",
            critical=True,
        )
    )

    valkey_start = time.time()
    valkey_ok = await redis_client.ping()
    valkey_duration = time.time() - valkey_start
    SERVICE_UP.labels(service="valkey").set(1 if valkey_ok else 0)
    SERVICE_LATENCY.labels(service="valkey").observe(valkey_duration)
    services.append(
        ServiceHealth(
            name="valkey",
            status="healthy" if valkey_ok else "unhealthy",
            latency_ms=round(valkey_duration * 1000, 2),
            message="Valkey connected" if valkey_ok else "Connection failed",
            description="Cache",
            critical=True,
        )
    )

    # --- TCP checks for remaining services (concurrent) ---
    tcp_services = [s for s in get_service_checks() if s["check"] == "tcp"]
    loop = asyncio.get_event_loop()
    tcp_results = await asyncio.gather(
        *[
            loop.run_in_executor(
                None, check_tcp_connection, svc["host"], svc["port"]
            )
            for svc in tcp_services
        ]
    )

    for svc, result in zip(tcp_services, tcp_results):
        connected = result["connected"]
        SERVICE_UP.labels(service=svc["name"]).set(1 if connected else 0)
        SERVICE_LATENCY.labels(service=svc["name"]).observe(result["latency_ms"] / 1000)
        services.append(
            ServiceHealth(
                name=svc["name"],
                status="healthy" if connected else "unhealthy",
                latency_ms=result["latency_ms"],
                message=None if connected else result["error"],
                description=svc["description"],
                critical=svc["critical"],
            )
        )

    # Determine overall status (only critical services affect it)
    critical_services = [s for s in services if s.critical]
    all_healthy = all(s.status == "healthy" for s in critical_services)
    any_healthy = any(s.status == "healthy" for s in critical_services)

    if all_healthy:
        overall = "healthy"
    elif any_healthy:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthCheckResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


async def check_database() -> bool:
    """Check database connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


def check_tcp_connection(host: str, port: int, timeout: float = 2.0) -> dict:
    """Test TCP connectivity to a host:port."""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        latency = (time.time() - start) * 1000
        sock.close()
        return {
            "connected": result == 0,
            "latency_ms": round(latency, 2),
            "error": None if result == 0 else f"Connection refused (code: {result})"
        }
    except socket.timeout:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": "Connection timed out"
        }
    except socket.gaierror as e:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": f"DNS resolution failed: {e}"
        }
    except Exception as e:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": str(e)
        }


@router.get("/api/v1/connectivity")
async def connectivity_matrix():
    """
    Test connectivity between services for micro-segmentation demo.
    Returns status of all service-to-service connections.
    """
    connections = []

    # API Server -> PostgreSQL
    db_result = check_tcp_connection(settings.database_host, settings.database_port)
    connections.append({
        "id": "api-to-db",
        "source": "API Server",
        "destination": "PostgreSQL",
        "port": settings.database_port,
        "protocol": "TCP",
        "status": "connected" if db_result["connected"] else "blocked",
        "latency_ms": db_result["latency_ms"],
        "error": db_result["error"],
    })

    # API Server -> Valkey
    valkey_result = check_tcp_connection(settings.redis_host, settings.redis_port)
    connections.append({
        "id": "api-to-valkey",
        "source": "API Server",
        "destination": "Valkey",
        "port": settings.redis_port,
        "protocol": "TCP",
        "status": "connected" if valkey_result["connected"] else "blocked",
        "latency_ms": valkey_result["latency_ms"],
        "error": valkey_result["error"],
    })

    # Fetch ADSB-Sync's own connectivity tests
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{settings.adsb_sync_host}:{settings.adsb_sync_port}/connectivity", timeout=5.0)
            adsb_connections = resp.json()
    except Exception:
        adsb_connections = [
            {"id": "adsb-to-valkey", "source": "ADSB-Sync", "destination": "Valkey", "port": settings.redis_port, "protocol": "TCP", "status": "blocked", "latency_ms": 0, "error": "ADSB-Sync unreachable"},
            {"id": "adsb-to-opensky", "source": "ADSB-Sync", "destination": "OpenSky Network", "port": 443, "protocol": "HTTPS", "status": "blocked", "latency_ms": 0, "error": "ADSB-Sync unreachable"},
        ]

    connections.extend(adsb_connections)

    # Count stats
    total = len(connections)
    connected = sum(1 for c in connections if c["status"] == "connected")
    blocked = total - connected

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "connected": connected,
            "blocked": blocked,
            "status": "healthy" if blocked == 0 else "degraded" if connected > 0 else "unhealthy"
        },
        "connections": connections
    }
