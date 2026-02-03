"""Celery application configuration."""

from celery import Celery
from app.config import settings
from app.logging_config import setup_logging

# Initialize logging for Celery workers
setup_logging(log_dir=settings.log_dir, log_level=settings.log_level)

# Create Celery app
celery_app = Celery(
    "ai_document_processing",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=4,  # Allow prefetching for better queue throughput with gevent
    worker_max_tasks_per_child=1000,

    # --- CHORD/GROUP CONFIGURATION ---
    # Required for chord to work properly and prevent deadlocks
    result_extended=True,  # Store extended task result metadata (required for chord)
    result_expires=3600,  # Results expire after 1 hour (prevents memory buildup)

    # Chord-specific settings
    task_ignore_result=False,  # Tasks must NOT ignore results for chord to work
    chord_propagate_exceptions=True,  # Propagate exceptions in chord
    task_always_eager=False,  # Never run tasks eagerly (required for chord)
    # --- END CHORD/GROUP CONFIGURATION ---

    # Beat schedule for periodic tasks (HITL SLA monitoring)
    beat_schedule={
        'check-sla-breaches-every-5-minutes': {
            'task': 'app.tasks.sla_monitor.check_sla_breaches',
            'schedule': 300.0,  # Every 5 minutes (300 seconds)
            'options': {
                'queue': 'default',
                'expires': 290,  # Expire before next scheduled run
            }
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
