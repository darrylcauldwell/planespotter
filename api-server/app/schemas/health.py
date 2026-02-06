from pydantic import BaseModel, Field
from datetime import datetime


class ServiceHealth(BaseModel):
    """Individual service health status."""

    name: str
    status: str = Field(..., description="healthy, unhealthy, or degraded")
    latency_ms: float | None = Field(None, description="Response time in milliseconds")
    message: str | None = None
    description: str | None = None
    critical: bool = True


class HealthCheckResponse(BaseModel):
    """Overall system health check response."""

    status: str = Field(..., description="Overall status")
    timestamp: datetime
    services: list[ServiceHealth]
