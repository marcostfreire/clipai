"""
Lightweight HTTP healthcheck server for Celery worker.

This server runs alongside Celery to respond to Railway's healthcheck requests.
It runs in a separate thread and doesn't interfere with Celery's operation.
"""

import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

logger = logging.getLogger(__name__)

# Port for healthcheck server - Railway will auto-detect this
HEALTHCHECK_PORT = int(os.environ.get("PORT", 8080))


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler that responds to healthcheck requests."""

    def log_message(self, format, *args):
        """Suppress default logging to keep logs clean."""
        pass

    def do_GET(self):
        """Handle GET requests - respond to /health endpoint."""
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "service": "celery-worker"}')
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error": "not found"}')

    def do_HEAD(self):
        """Handle HEAD requests for healthcheck."""
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def start_healthcheck_server():
    """Start the healthcheck server in a separate daemon thread."""
    try:
        server = HTTPServer(("0.0.0.0", HEALTHCHECK_PORT), HealthCheckHandler)
        logger.info(f"Healthcheck server starting on port {HEALTHCHECK_PORT}")

        # Run server in a daemon thread so it doesn't block shutdown
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        logger.info(
            f"Healthcheck server running at http://0.0.0.0:{HEALTHCHECK_PORT}/health"
        )
        return server
    except Exception as e:
        logger.error(f"Failed to start healthcheck server: {e}")
        raise


if __name__ == "__main__":
    # Test the healthcheck server standalone
    logging.basicConfig(level=logging.INFO)
    server = start_healthcheck_server()
    print(f"Test server running on port {HEALTHCHECK_PORT}. Press Ctrl+C to stop.")
    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
