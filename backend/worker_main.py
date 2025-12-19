#!/usr/bin/env python3
"""
Worker entry point that starts healthcheck server alongside Celery.

This script is used as the entry point for the Railway worker service.
It starts a lightweight HTTP server for healthchecks, then launches Celery.
"""

import os
import sys
import logging
import subprocess
import signal
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Global reference to celery process for cleanup
celery_process = None


def main():
    """Start healthcheck server and Celery worker."""
    global celery_process

    logger.info("=" * 50)
    logger.info("CELERY WORKER WITH HEALTHCHECK SERVER")
    logger.info("=" * 50)

    # Start healthcheck server FIRST
    logger.info("Starting healthcheck server...")
    from app.utils.healthcheck_server import start_healthcheck_server

    try:
        healthcheck_server = start_healthcheck_server()
        logger.info("✓ Healthcheck server started successfully")
    except Exception as e:
        logger.error(f"✗ Failed to start healthcheck server: {e}")
        # Continue anyway - Celery is more important

    # Give healthcheck server a moment to fully start
    time.sleep(0.5)

    # Now start Celery worker as subprocess
    logger.info("Starting Celery worker...")

    celery_args = [
        "celery",
        "-A",
        "app.tasks.celery_tasks",
        "worker",
        "--loglevel=info",
        "--concurrency=1",
        "--pool=solo",
        "--prefetch-multiplier=1",
    ]

    logger.info(f"Celery command: {' '.join(celery_args)}")

    # Handle shutdown gracefully
    def shutdown_handler(signum, frame):
        logger.info("Received shutdown signal, stopping Celery...")
        if celery_process:
            celery_process.terminate()
            try:
                celery_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                celery_process.kill()
        logger.info("Shutdown complete")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Start Celery as subprocess (keeps healthcheck thread alive)
    try:
        celery_process = subprocess.Popen(celery_args)
        logger.info(f"Celery worker started with PID {celery_process.pid}")

        # Wait for Celery to exit
        exit_code = celery_process.wait()
        logger.info(f"Celery worker exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.error(f"Failed to start Celery: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
