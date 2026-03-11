from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "stratix",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Tashkent",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    worker_max_tasks_per_child=100,
    result_expires=3600,
)

celery_app.autodiscover_tasks(
    [
        "src.workers.crm_tasks",
        "src.workers.notification_tasks",
        "src.workers.sync_tasks",
    ]
)
