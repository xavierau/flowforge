"""
Worker Startup Script

Starts all Conductor workers for workflow execution.

Usage:
    python -m app.orchestration.start_workers

Environment Variables:
    CONDUCTOR_SERVER_URL: Conductor server URL (default: http://localhost:8080/api)
    WORKER_THREADS: Number of worker threads (default: 4)
    WORKER_POLL_INTERVAL: Polling interval in ms (default: 1000)
"""

import os
import sys
import logging
from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration

from app.orchestration.workers import (
    ExtractionWorker,
    PythonWorker,
    HttpRequestWorker,
    ConditionWorker,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/conductor_workers.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Start all Conductor workers."""

    # Load configuration from environment
    conductor_url = os.getenv(
        "CONDUCTOR_SERVER_URL",
        "http://localhost:8080/api"
    )
    thread_count = int(os.getenv("WORKER_THREADS", "4"))
    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL", "1000"))

    logger.info("=" * 80)
    logger.info("Starting Conductor Workers")
    logger.info("=" * 80)
    logger.info(f"Conductor Server: {conductor_url}")
    logger.info(f"Worker Threads: {thread_count}")
    logger.info(f"Poll Interval: {poll_interval}ms")
    logger.info("-" * 80)

    # Configure Conductor client
    config = Configuration(
        server_api_url=conductor_url,
        debug=False,
        authentication_settings=None,
    )

    # Initialize all workers
    workers = [
        ExtractionWorker(),
        PythonWorker(),
        HttpRequestWorker(),
        ConditionWorker(),
    ]

    logger.info("Initialized workers:")
    for worker in workers:
        logger.info(f"  - {worker.__class__.__name__} ({worker.task_definition_name})")

    logger.info("-" * 80)
    logger.info("Starting task polling...")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 80)

    # Start task handler
    try:
        with TaskHandler(
            workers=workers,
            configuration=config,
            scan_for_annotated_workers=False,
            import_modules=[]
        ) as task_handler:
            task_handler.start_processes()

            # Keep running until interrupted
            import time
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n" + "=" * 80)
        logger.info("Shutting down workers...")
        logger.info("=" * 80)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
