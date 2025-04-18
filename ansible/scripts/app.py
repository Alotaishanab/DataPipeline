from celery import Celery

app = Celery(
    'worker',
    broker='redis://mgmtnode:6379/0',
    backend='redis://mgmtnode:6379/1'
)

app.conf.task_default_queue = 'celery'
app.conf.task_routes = {
    'celery_worker.*': {'queue': 'celery'}
}