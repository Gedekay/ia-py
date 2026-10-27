from celery import Celery

from app.core.config import get_settings


settings = get_settings()
celery_app = Celery(
    "saajd",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_routes={"app.workers.tasks.*": {"queue": "saajd"}},
    beat_schedule={
        "purge-old-documents-daily": {
            "task": "app.workers.tasks.purge_old_documents_task",
            "schedule": 86400.0,
        }
    },
)