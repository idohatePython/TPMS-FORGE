from celery import Celery

from backend.app.core.config import settings
from backend.app.core.logging import configure_logging

configure_logging()

celery_app = Celery(
    "tpms_forge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "worker.tasks.model_generation",
        "worker.tasks.slicing_gcode",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=60 * 60,
    task_soft_time_limit=55 * 60,
    worker_hijack_root_logger=False,
)

