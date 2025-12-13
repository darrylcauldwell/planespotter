import httpx
from app.config import settings


class APIClient:
    """HTTP client for communicating with the API server."""

    def __init__(self):
        self.base_url = settings.api_server_url

    async def search_aircraft(
        self,
        registration: str | None = None,
        icao24: str | None = None,
        manufacturer: str | None = None,
        model: str | None = None,
        operator: str | None = None,
        owner: str | None = None,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """Search aircraft registry."""
        params = {
            k: v
            for k, v in {
                "registration": registration,
                "icao24": icao24,
                "manufacturer": manufacturer,
                "model": model,
                "operator": operator,
                "owner": owner,
                "status": status,
                "page": page,
                "per_page": per_page,
            }.items()
            if v
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/aircraft", params=params
            )
            response.raise_for_status()
            return response.json()

    async def get_aircraft(self, icao24: str) -> dict | None:
        """Get aircraft details with position."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/api/v1/aircraft/{icao24}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def get_health(self) -> dict | None:
        """Get system health status."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/health")
                response.raise_for_status()
                return response.json()
        except Exception:
            return None

    async def get_connectivity(self) -> dict | None:
        """Get connectivity matrix between services."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{self.base_url}/api/v1/connectivity")
                response.raise_for_status()
                return response.json()
        except Exception:
            return None


api_client = APIClient()
