import time
import socket
from datetime import datetime, timezone
from fastapi import APIRouter
from sqlalchemy import text
from app.database import AsyncSessionLocal
from app.services.redis_client import redis_client
from app.schemas.health import ServiceHealth, HealthCheckResponse
from app.config import settings

router = APIRouter(tags=["health"])


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

    # Check database
    db_start = time.time()
    db_ok = await check_database()
    db_latency = (time.time() - db_start) * 1000
    services.append(
        ServiceHealth(
            name="database",
            status="healthy" if db_ok else "unhealthy",
            latency_ms=round(db_latency, 2),
            message="PostgreSQL connected" if db_ok else "Connection failed",
        )
    )

    # Check Valkey
    valkey_start = time.time()
    valkey_ok = await redis_client.ping()
    valkey_latency = (time.time() - valkey_start) * 1000
    services.append(
        ServiceHealth(
            name="valkey",
            status="healthy" if valkey_ok else "unhealthy",
            latency_ms=round(valkey_latency, 2),
            message="Valkey connected" if valkey_ok else "Connection failed",
        )
    )

    # Determine overall status
    all_healthy = all(s.status == "healthy" for s in services)
    any_healthy = any(s.status == "healthy" for s in services)

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

    # Test external connectivity - OpenSky API
    opensky_result = check_tcp_connection("opensky-network.org", 443, timeout=5.0)
    connections.append({
        "id": "api-to-opensky",
        "source": "API Server",
        "destination": "OpenSky Network",
        "port": 443,
        "protocol": "HTTPS",
        "status": "connected" if opensky_result["connected"] else "blocked",
        "latency_ms": opensky_result["latency_ms"],
        "error": opensky_result["error"],
    })

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
