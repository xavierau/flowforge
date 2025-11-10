"""Logging configuration for the application."""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> None:
    """
    Configure logging to write to both console and rotating log files.

    Args:
        log_dir: Directory to store log files (default: "logs")
        log_level: Logging level (default: "INFO")
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Define log file paths
    app_log_file = log_path / "app.log"
    celery_log_file = log_path / "celery.log"
    error_log_file = log_path / "errors.log"

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)

    # Application log file handler (rotating)
    app_file_handler = logging.handlers.RotatingFileHandler(
        filename=app_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    app_file_handler.setLevel(logging.DEBUG)
    app_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(app_file_handler)

    # Celery-specific log file handler (rotating)
    celery_file_handler = logging.handlers.RotatingFileHandler(
        filename=celery_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    celery_file_handler.setLevel(logging.DEBUG)
    celery_file_handler.setFormatter(detailed_formatter)

    # Add celery handler to celery loggers
    celery_logger = logging.getLogger("celery")
    celery_logger.addHandler(celery_file_handler)
    celery_logger.setLevel(logging.DEBUG)

    # Task-specific loggers
    for task_module in ["app.tasks.extractor", "app.tasks.pdf_processor"]:
        task_logger = logging.getLogger(task_module)
        task_logger.addHandler(celery_file_handler)
        task_logger.setLevel(logging.DEBUG)

    # Error log file handler (rotating) - only errors and critical
    error_file_handler = logging.handlers.RotatingFileHandler(
        filename=error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Log startup message
    root_logger.info(f"Logging initialized - logs directory: {log_path.absolute()}")
    root_logger.info(f"Log files: app.log, celery.log, errors.log")


def get_task_logger(task_name: str) -> logging.Logger:
    """
    Get a logger instance for a specific task.

    Args:
        task_name: Name of the task

    Returns:
        Logger instance configured for the task
    """
    return logging.getLogger(f"celery.task.{task_name}")
