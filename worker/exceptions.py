class WorkerTaskError(RuntimeError):
    """Base error for Celery task failures that should be recorded on task metadata."""

