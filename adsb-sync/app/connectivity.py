import json
import socket
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.config import settings


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
            "error": None if result == 0 else f"Connection refused (code: {result})",
        }
    except socket.timeout:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": "Connection timed out",
        }
    except socket.gaierror as e:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": f"DNS resolution failed: {e}",
        }
    except Exception as e:
        return {
            "connected": False,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": str(e),
        }


def get_connectivity():
    """Test ADSB-Sync's outbound connections and return results."""
    connections = []

    # ADSB-Sync -> Valkey
    valkey_result = check_tcp_connection(settings.redis_host, settings.redis_port)
    connections.append({
        "id": "adsb-to-valkey",
        "source": "ADSB-Sync",
        "destination": "Valkey",
        "port": settings.redis_port,
        "protocol": "TCP",
        "status": "connected" if valkey_result["connected"] else "blocked",
        "latency_ms": valkey_result["latency_ms"],
        "error": valkey_result["error"],
    })

    # ADSB-Sync -> OpenSky Network
    opensky_result = check_tcp_connection("opensky-network.org", 443, timeout=5.0)
    connections.append({
        "id": "adsb-to-opensky",
        "source": "ADSB-Sync",
        "destination": "OpenSky Network",
        "port": 443,
        "protocol": "HTTPS",
        "status": "connected" if opensky_result["connected"] else "blocked",
        "latency_ms": opensky_result["latency_ms"],
        "error": opensky_result["error"],
    })

    return connections


class CustomHandler(BaseHTTPRequestHandler):
    """HTTP handler serving Prometheus metrics and connectivity endpoint."""

    def do_GET(self):
        if self.path == "/metrics":
            output = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
        elif self.path == "/connectivity":
            connections = get_connectivity()
            body = json.dumps(connections).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass


def start_custom_server(port: int):
    """Start a threaded HTTP server for metrics and connectivity."""
    server = HTTPServer(("0.0.0.0", port), CustomHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
